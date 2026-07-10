import os
import logging
import socket
import sys
import threading
import time
import ctypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parents[2]
for path in [
    ROOT_DIR,
    ROOT_DIR / "backend" / "core",
    ROOT_DIR / "backend" / "models",
    ROOT_DIR / "agent" / "collectors",
    ROOT_DIR / "agent" / "client",
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from collect_hardware import collect_current_active_path
from login_tracker import close_active_sessions, detect_login, load_sessions, record_login, save_sessions
from session_manager import get_current_session_info
from api_client import (
    get_latest_active_application_for_host as get_latest_active_application_for_host_from_api,
    has_session_event_signature,
    list_active_applications_history,
    send_activity_sample,
    send_alert,
    send_application,
    send_session,
)


POLL_INTERVAL_SECONDS = 2
LOGIN_POLL_INTERVAL_SECONDS = 1
LOCK_FALLBACK_DEBOUNCE_SECONDS = 2
UNLOCK_FALLBACK_DEBOUNCE_SECONDS = 2
IDLE_THRESHOLD_SECONDS = int(os.environ.get("IDLE_THRESHOLD_SECONDS") or os.environ.get("ASSET_SENTINEL_IDLE_THRESHOLD_SECONDS", "60"))
logger = logging.getLogger("asset_sentinel.active_application_monitor")

_monitor_lock = threading.Lock()
_monitor_started = False
_login_monitor_started = False
_last_signature_by_host: Dict[str, tuple] = {}
_lock_screen_observed = False
_last_lock_fallback_at = 0.0
_last_unlock_fallback_at = 0.0


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_user_idle_seconds() -> Optional[int]:
    try:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        ctypes.windll.kernel32.GetTickCount.restype = ctypes.c_uint32
        tick_count = ctypes.windll.kernel32.GetTickCount()
        elapsed_ms = (int(tick_count) - int(info.dwTime)) & 0xFFFFFFFF
        return max(0, int(elapsed_ms / 1000))
    except Exception as exc:
        logger.debug("Could not read Windows last input time: %s", exc)
        return None


def is_windows_locked() -> Optional[bool]:
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32
        DESKTOP_SWITCHDESKTOP = 0x0100
        desktop = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if not desktop:
            return True
        try:
            return not bool(user32.SwitchDesktop(desktop))
        finally:
            user32.CloseDesktop(desktop)
    except Exception as exc:
        logger.debug("Could not determine Windows lock state from input desktop: %s", exc)
        return None


def _locked_activity_record() -> Dict[str, Any]:
    timestamp = datetime.now().astimezone().isoformat()
    return {
        "hostname": socket.gethostname(),
        "username": _current_username(),
        "application_name": "LockApp",
        "executable_name": "LockApp.exe",
        "window_title": "Windows Lock Screen",
        "process_path": "Windows Lock Screen",
        "timestamp": timestamp,
        "user_idle_seconds": get_user_idle_seconds(),
        "idle_threshold_seconds": IDLE_THRESHOLD_SECONDS,
        "is_user_idle": False,
        "windows_locked": True,
    }


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
        send_application(history[-1], record_sample=False)
    except Exception as exc:
        print(f"[WARNING] Could not write active application history to PostgreSQL: {exc}")


def _current_username() -> str:
    return (
        os.environ.get("USERNAME")
        or os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or "Unknown"
    )


def activity_state_from_record(record: Optional[Dict[str, Any]]) -> str:
    if not record:
        return "active"
    if record.get("windows_locked"):
        return "locked"
    if record.get("is_user_idle"):
        return "idle"
    return "active"


def _log_activity_sample_state(
    record: Dict[str, Any],
    source: str,
    heartbeat_sent: str = "separate_15s_loop",
    usage_sync_sent: str = "attempting",
) -> None:
    logger.info(
        "Activity sample state: source=%s foreground_app=%s windows_idle_seconds=%s idle_threshold=%s is_locked=%s final_activity_state=%s heartbeat_sent=%s usage_sync_sent=%s",
        source,
        record.get("executable_name") or record.get("application_name"),
        record.get("user_idle_seconds"),
        record.get("idle_threshold_seconds"),
        bool(record.get("windows_locked")),
        activity_state_from_record(record),
        heartbeat_sent,
        usage_sync_sent,
    )


def collect_active_application_record() -> Optional[Dict[str, Any]]:
    locked = is_windows_locked()
    if locked is True:
        return _locked_activity_record()

    activity = collect_current_active_path()
    executable_name = activity.get("active_process_name")
    window_title = activity.get("active_window_title")

    if not executable_name and not window_title:
        return None

    application_name = executable_name.rsplit(".", 1)[0] if executable_name else "Unknown"
    timestamp = datetime.now().astimezone().isoformat()
    process_path = activity.get("active_process_path")
    idle_seconds = get_user_idle_seconds()

    return {
        "hostname": socket.gethostname(),
        "username": _current_username(),
        "application_name": application_name,
        "executable_name": executable_name or "Unknown",
        "window_title": window_title or "Unknown",
        "process_path": process_path,
        "timestamp": timestamp,
        "user_idle_seconds": idle_seconds,
        "idle_threshold_seconds": IDLE_THRESHOLD_SECONDS,
        "is_user_idle": bool(idle_seconds is not None and idle_seconds >= IDLE_THRESHOLD_SECONDS),
        "windows_locked": bool(locked is True or "lockapp" in (executable_name or "").lower() or "lock screen" in (window_title or "").lower()),
    }


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
        if not _lock_screen_observed and now - _last_lock_fallback_at >= LOCK_FALLBACK_DEBOUNCE_SECONDS:
            session_info = get_current_session_info()
            timestamp = str(record.get("timestamp") or datetime.now().astimezone().isoformat())
            synthetic_record_id = (
                f"lockapp-lock:{session_info.get('hostname')}:"
                f"{session_info.get('username')}:{int(now)}"
            )
            if not has_session_event_signature(session_info.get("hostname"), synthetic_record_id):
                lock_record = {
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
                }
                active_sessions = load_sessions()
                updated_sessions = close_active_sessions(
                    active_sessions,
                    {
                        **session_info,
                        "force_close_active_sessions": True,
                        "latest_logout_timestamp": timestamp,
                        "latest_logout_event_id": "LOCKAPP_LOCK",
                        "latest_logout_event_record_id": synthetic_record_id,
                    },
                    timestamp,
                )
                save_sessions(updated_sessions)
                send_session(lock_record)
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
    if now - _last_unlock_fallback_at < UNLOCK_FALLBACK_DEBOUNCE_SECONDS:
        _lock_screen_observed = False
        return

    session_info = get_current_session_info()
    timestamp = str(record.get("timestamp") or datetime.now().astimezone().isoformat())
    synthetic_record_id = (
        f"lockapp-unlock:{session_info.get('hostname')}:"
        f"{session_info.get('username')}:{int(now)}"
    )
    if has_session_event_signature(session_info.get("hostname"), synthetic_record_id):
        _lock_screen_observed = False
        return

    record_login({
        **session_info,
        "hostname": session_info.get("hostname") or socket.gethostname(),
        "login_timestamp": timestamp,
        "login_source": "windows_unlock_observed",
        "windows_event_id": "LOCKAPP_UNLOCK",
        "windows_event_record_id": synthetic_record_id,
    })
    send_alert(
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
        "Unlock detected from LockApp fallback and started a new current session: user=%s host=%s record_id=%s",
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
            _record_unlock_fallback_if_needed(record)
            if record:
                try:
                    _log_activity_sample_state(record, "active_application_monitor")
                    send_activity_sample(record)
                except Exception as sample_exc:
                    logger.exception("Activity session sample failed and will continue: %s", sample_exc)
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
        return list_active_applications_history()
    except Exception as exc:
        print(f"[WARNING] Could not load latest active applications from PostgreSQL: {exc}")
        return []


def get_latest_active_application_for_host(hostname: str) -> Optional[Dict[str, Any]]:
    try:
        return get_latest_active_application_for_host_from_api(hostname)
    except Exception as exc:
        print(f"[WARNING] Could not load latest active application for {hostname}: {exc}")
        return None
