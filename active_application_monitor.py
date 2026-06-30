import os
import logging
import socket
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from collect_hardware import collect_current_active_path
from login_tracker import detect_login
from session_manager import get_current_session_info
from storage import (
    append_active_application,
    append_alert,
    append_session,
    get_latest_active_application_for_host as get_latest_active_application_for_host_from_db,
    get_latest_active_applications as get_latest_active_applications_from_db,
    has_session_event_signature,
    list_active_applications_history,
    update_asset_heartbeat,
)


POLL_INTERVAL_SECONDS = 2
LOGIN_POLL_INTERVAL_SECONDS = 5
logger = logging.getLogger("asset_sentinel.active_application_monitor")

_monitor_lock = threading.Lock()
_monitor_started = False
_login_monitor_started = False
_last_signature_by_host: Dict[str, tuple] = {}
_lock_screen_observed = False
_last_lock_fallback_at = 0.0
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
    timestamp = datetime.now().astimezone().isoformat()
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
        record.get("application_name") or record.get("application") or record.get("executable_name"),
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
    user application is a real lock/unlock boundary.
    """
    global _lock_screen_observed, _last_lock_fallback_at, _last_unlock_fallback_at

    if _is_lock_app(record):
        now = time.time()
        if not _lock_screen_observed and now - _last_lock_fallback_at >= 15:
            session_info = get_current_session_info()
            timestamp = datetime.now().astimezone().isoformat()
            synthetic_record_id = (
                f"lockapp-lock:{session_info.get('hostname')}:"
                f"{session_info.get('username')}:{int(now)}"
            )
            if not has_session_event_signature(session_info.get("hostname"), synthetic_record_id):
                append_session({
                    "event_type": "LOGOUT",
                    "username": session_info.get("username"),
                    "hostname": session_info.get("hostname") or socket.gethostname(),
                    "ip_address": session_info.get("ip_address"),
                    "session_id": session_info.get("session_id"),
                    "login_timestamp": session_info.get("login_timestamp"),
                    "logout_timestamp": timestamp,
                    "session_duration": "Locked",
                    "active": False,
                    "device_status": None,
                    "last_seen": timestamp,
                    "login_source": "windows_lock_observed",
                    "windows_event_id": "LOCKAPP_LOCK",
                    "windows_event_record_id": synthetic_record_id,
                    "recorded_at": timestamp,
                })
                logger.info(
                    "Logout detected from LockApp fallback: user=%s host=%s record_id=%s",
                    session_info.get("username"),
                    session_info.get("hostname"),
                    synthetic_record_id,
                )
                _last_lock_fallback_at = now
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

    append_session({
        "event_type": "LOGIN",
        "username": session_info.get("username"),
        "hostname": session_info.get("hostname") or socket.gethostname(),
        "ip_address": session_info.get("ip_address"),
        "session_id": session_info.get("session_id"),
        "login_timestamp": timestamp,
        "logout_timestamp": None,
        "session_duration": "Active",
        "active": True,
        "device_status": None,
        "last_seen": timestamp,
        "login_source": "windows_unlock_observed",
        "windows_event_id": "LOCKAPP_UNLOCK",
        "windows_event_record_id": synthetic_record_id,
        "recorded_at": timestamp,
    })
    append_alert(
        "UNLOCK",
        session_info.get("hostname") or socket.gethostname(),
        "LOW",
        {
            "username": session_info.get("username"),
            "login_source": "windows_unlock_observed",
            "windows_event_id": "LOCKAPP_UNLOCK",
            "windows_event_record_id": synthetic_record_id,
            "description": "Windows unlock observed from LockApp transition.",
        },
        timestamp,
    )
    logger.info(
        "Login detected from LockApp fallback: user=%s host=%s record_id=%s",
        session_info.get("username"),
        session_info.get("hostname"),
        synthetic_record_id,
    )
    _last_unlock_fallback_at = now
    _lock_screen_observed = False


def _append_if_changed(record: Dict[str, Any]) -> None:
    signature = _record_signature(record)
    hostname = record.get("hostname") or socket.gethostname()
    with _monitor_lock:
        history = _read_activity_history()
        for latest in history:
            if (latest.get("hostname") or hostname) != hostname:
                continue
            if _record_signature(latest) == signature:
                _last_signature_by_host[hostname] = signature
                return
            break

        if _last_signature_by_host.get(hostname) == signature:
            return

        history.append(record)
        _write_activity_history(history)
        _last_signature_by_host[hostname] = signature
        logger.info(
            "Foreground application changed: hostname=%s application=%s window=%s",
            hostname,
            record.get("application_name") or record.get("application"),
            record.get("window_title"),
        )


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
    global _monitor_started, _lock_screen_observed

    with _monitor_lock:
        if _monitor_started:
            return
        history = _read_activity_history()
        if history:
            for record in history:
                hostname = record.get("hostname")
                if hostname and hostname not in _last_signature_by_host:
                    _last_signature_by_host[hostname] = _record_signature(record)
            _lock_screen_observed = _is_lock_app(history[0])
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
