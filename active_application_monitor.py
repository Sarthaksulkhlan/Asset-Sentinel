import os
import socket
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from collect_hardware import collect_current_active_path
from login_tracker import detect_login, record_login
from session_manager import get_current_session_info
from storage import (
    append_active_application,
    get_latest_active_application_for_host as get_latest_active_application_for_host_from_db,
    get_latest_active_applications as get_latest_active_applications_from_db,
    has_session_event_signature,
    list_active_applications_history,
    update_asset_heartbeat,
)


POLL_INTERVAL_SECONDS = 2
LOGIN_POLL_INTERVAL_SECONDS = 5

_monitor_lock = threading.Lock()
_monitor_started = False
_login_monitor_started = False
_last_signature: Optional[tuple] = None
_lock_screen_observed = False
_last_unlock_fallback_at = 0.0


def _read_activity_history() -> List[Dict[str, Any]]:
    try:
        return list_active_applications_history()
    except Exception as exc:
        print(f"[WARNING] Could not read active application history from PostgreSQL: {exc}")
        return []


def _write_activity_history(history: List[Dict[str, Any]]) -> None:
    if not history:
        return
    try:
        append_active_application(history[-1])
    except Exception as exc:
        print(f"[WARNING] Could not write active application history to PostgreSQL: {exc}")


def _current_username() -> str:
    return (
        os.environ.get("USERNAME")
        or os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or "Unknown"
    )


def collect_active_application_record() -> Optional[Dict[str, Any]]:
    activity = collect_current_active_path()
    executable_name = activity.get("active_process_name")
    window_title = activity.get("active_window_title")

    if not executable_name and not window_title:
        return None

    application_name = executable_name.rsplit(".", 1)[0] if executable_name else "Unknown"
    timestamp = datetime.now().isoformat()
    process_path = activity.get("active_process_path")

    return {
        "hostname": socket.gethostname(),
        "username": _current_username(),
        "application_name": application_name,
        "executable_name": executable_name or "Unknown",
        "window_title": window_title or "Unknown",
        "process_path": process_path,
        "timestamp": timestamp,
    }


def _usage_snapshot() -> tuple:
    try:
        import psutil
        return round(float(psutil.cpu_percent(interval=None)), 2), round(float(psutil.virtual_memory().percent), 2)
    except Exception:
        return None, None


def _record_signature(record: Dict[str, Any]) -> tuple:
    return (
        record.get("hostname"),
        record.get("username"),
        record.get("executable_name"),
        record.get("window_title"),
    )


def _is_lock_app(record: Optional[Dict[str, Any]]) -> bool:
    if not record:
        return False
    values = [
        record.get("application_name"),
        record.get("executable_name"),
        record.get("window_title"),
        record.get("process_path"),
    ]
    return any("lockapp" in str(value or "").lower() for value in values)


def _record_unlock_fallback_if_needed(record: Optional[Dict[str, Any]]) -> None:
    """
    Non-admin fallback for Windows unlocks.

    Security 4624/4634 remains the preferred source, but normal desktop
    processes often cannot open the Security log. The foreground monitor can
    still observe LockApp during Win+L; the transition from LockApp to the next
    user application is a real unlock boundary and should create a login row.
    """
    global _lock_screen_observed, _last_unlock_fallback_at

    if _is_lock_app(record):
        _lock_screen_observed = True
        return

    if not _lock_screen_observed or not record:
        return

    now = time.time()
    if now - _last_unlock_fallback_at < 15:
        _lock_screen_observed = False
        return

    session_info = get_current_session_info()
    timestamp = datetime.now().astimezone().isoformat()
    synthetic_record_id = (
        f"lockapp-unlock:{session_info.get('hostname')}:"
        f"{session_info.get('username')}:{int(now)}"
    )
    if has_session_event_signature(session_info.get("hostname"), synthetic_record_id):
        _lock_screen_observed = False
        return

    session_info.update({
        "login_timestamp": timestamp,
        "login_source": "windows_unlock_observed",
        "windows_event_id": "LOCKAPP_UNLOCK",
        "windows_event_record_id": synthetic_record_id,
    })
    record_login(session_info)
    _last_unlock_fallback_at = now
    _lock_screen_observed = False


def _append_if_changed(record: Dict[str, Any]) -> None:
    global _last_signature

    signature = _record_signature(record)
    with _monitor_lock:
        history = _read_activity_history()
        if history:
            latest = history[-1]
            if _record_signature(latest) == signature:
                _last_signature = signature
                return

        if _last_signature == signature:
            return

        history.append(record)
        _write_activity_history(history)
        _last_signature = signature


def _monitor_loop() -> None:
    while True:
        try:
            record = collect_active_application_record()
            cpu_usage, ram_usage = _usage_snapshot()
            update_asset_heartbeat(socket.gethostname(), cpu_usage, ram_usage, record)
            _record_unlock_fallback_if_needed(record)
            if record:
                _append_if_changed(record)
        except Exception as exc:
            print(f"[WARNING] Active application monitor error: {exc}")
        time.sleep(POLL_INTERVAL_SECONDS)


def start_active_application_monitor() -> None:
    global _monitor_started, _last_signature, _lock_screen_observed

    with _monitor_lock:
        if _monitor_started:
            return
        history = _read_activity_history()
        if history:
            _last_signature = _record_signature(history[-1])
            _lock_screen_observed = _is_lock_app(history[-1])
        _monitor_started = True

    thread = threading.Thread(target=_monitor_loop, name="active-application-monitor", daemon=True)
    thread.start()
    print("[INFO] Active application monitor started.")


def _login_monitor_loop() -> None:
    while True:
        try:
            detect_login()
        except Exception as exc:
            print(f"[WARNING] Login event monitor error: {exc}")
        time.sleep(LOGIN_POLL_INTERVAL_SECONDS)


def start_login_event_monitor() -> None:
    global _login_monitor_started

    with _monitor_lock:
        if _login_monitor_started:
            return
        _login_monitor_started = True

    thread = threading.Thread(target=_login_monitor_loop, name="login-event-monitor", daemon=True)
    thread.start()
    print("[INFO] Windows login event monitor started.")


def get_latest_active_applications() -> List[Dict[str, Any]]:
    try:
        return get_latest_active_applications_from_db()
    except Exception as exc:
        print(f"[WARNING] Could not load latest active applications from PostgreSQL: {exc}")
        return []


def get_latest_active_application_for_host(hostname: str) -> Optional[Dict[str, Any]]:
    try:
        return get_latest_active_application_for_host_from_db(hostname)
    except Exception as exc:
        print(f"[WARNING] Could not load latest active application for {hostname}: {exc}")
        return None
