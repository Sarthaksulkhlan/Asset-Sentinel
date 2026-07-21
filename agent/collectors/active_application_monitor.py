import os
import logging
import socket
import sys
import threading
import time
import ctypes
import json
from datetime import datetime, timezone
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

from collect_hardware import collect_current_active_path, collect_foreground_diagnostics
from login_tracker import detect_login
from session_manager import get_latest_windows_logout_event, get_latest_windows_unlock_event
from api_client import (
    get_latest_active_application_for_host as get_latest_active_application_for_host_from_api,
    list_active_applications_history,
    send_activity_sample,
    send_application,
)


POLL_INTERVAL_SECONDS = 2
LOGIN_POLL_INTERVAL_SECONDS = 1
LOCK_FALLBACK_DEBOUNCE_SECONDS = 2
UNLOCK_FALLBACK_DEBOUNCE_SECONDS = 2
IDLE_THRESHOLD_SECONDS = int(os.environ.get("IDLE_THRESHOLD_SECONDS") or os.environ.get("ASSET_SENTINEL_IDLE_THRESHOLD_SECONDS", "60"))
logger = logging.getLogger("asset_sentinel.active_application_monitor")
WORKSTATION_STATE_PATH = ROOT_DIR / "logs" / "workstation_state.json"
WINDOWS_LOCK_EVENT_IDS = {"4800", "4779", "4634"}

_monitor_lock = threading.Lock()
_monitor_started = False
_login_monitor_started = False
_last_signature_by_host: Dict[str, tuple] = {}
_lock_screen_observed = False
_last_lock_fallback_at = 0.0
_last_unlock_fallback_at = 0.0


def _load_workstation_state() -> Dict[str, Any]:
    try:
        if WORKSTATION_STATE_PATH.exists():
            with WORKSTATION_STATE_PATH.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
                return state if isinstance(state, dict) else {}
    except Exception as exc:
        logger.warning("Could not read workstation state file %s: %s", WORKSTATION_STATE_PATH, exc)
    return {}


def _save_workstation_state(state: Dict[str, Any]) -> None:
    try:
        WORKSTATION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with WORKSTATION_STATE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
    except Exception as exc:
        logger.warning("Could not persist workstation state file %s: %s", WORKSTATION_STATE_PATH, exc)


def _state_key(hostname: Optional[str]) -> str:
    return hostname or socket.gethostname() or "Unknown"


def _current_workstation_state(hostname: Optional[str]) -> Optional[str]:
    state = _load_workstation_state()
    current = state.get(_state_key(hostname)) or {}
    if not isinstance(current, dict):
        return None
    value = current.get("state")
    return str(value) if value else None


def _apply_workstation_state(hostname: Optional[str], locked: bool) -> bool:
    """
    Persist the workstation lock state and return true only for real transitions.

    Unknown -> locked initializes state without creating a LockApp event because
    a startup/polling race is not proof that Windows just entered the lock
    screen. Unlocked -> locked is the only transition that emits LockApp.
    """
    state = _load_workstation_state()
    key = _state_key(hostname)
    previous = (state.get(key) or {}).get("state")
    current = "locked" if locked else "unlocked"
    if previous == current:
        now = datetime.now(timezone.utc)
        updated_at = _event_timestamp({"event_timestamp": (state.get(key) or {}).get("updated_at")})
        if updated_at is None or (now - updated_at).total_seconds() >= 60:
            state[key] = {
                **(state.get(key) if isinstance(state.get(key), dict) else {}),
                "state": current,
                "updated_at": now.isoformat(),
            }
            _save_workstation_state(state)
        return False

    state[key] = {
        "state": current,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_workstation_state(state)

    if previous is None:
        logger.info(
            "Workstation state initialized: hostname=%s state=%s; no synthetic transition event emitted.",
            key,
            current,
        )
        return not locked

    logger.info("Workstation state transition: hostname=%s %s -> %s", key, previous, current)
    return previous == "unlocked" and current == "locked"


def _latest_confirmed_windows_lock_event(username: Optional[str]) -> Optional[Dict[str, Any]]:
    try:
        event = get_latest_windows_logout_event(username)
    except Exception as exc:
        logger.debug("Could not read latest Windows lock event for LockApp timeline proof: %s", exc)
        return None
    if not event or str(event.get("event_id") or "") not in WINDOWS_LOCK_EVENT_IDS:
        return None
    return event


def _latest_confirmed_windows_unlock_event(username: Optional[str]) -> Optional[Dict[str, Any]]:
    try:
        return get_latest_windows_unlock_event(username)
    except Exception as exc:
        logger.debug("Could not read latest Windows unlock event for LockApp timeline proof: %s", exc)
        return None


def _event_timestamp(event: Optional[Dict[str, Any]]) -> Optional[datetime]:
    value = (event or {}).get("event_timestamp")
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _state_updated_at(hostname: Optional[str]) -> Optional[datetime]:
    state = _load_workstation_state()
    current = state.get(_state_key(hostname)) or {}
    if not isinstance(current, dict):
        return None
    return _event_timestamp({"event_timestamp": current.get("updated_at")})


def _lock_event_is_current(hostname: Optional[str], lock_event: Optional[Dict[str, Any]], unlock_event: Optional[Dict[str, Any]]) -> bool:
    lock_time = _event_timestamp(lock_event)
    if not lock_time:
        return False
    unlock_time = _event_timestamp(unlock_event)
    if unlock_time and unlock_time >= lock_time:
        return False
    state_time = _state_updated_at(hostname)
    if _current_workstation_state(hostname) == "unlocked" and state_time and state_time >= lock_time:
        return False
    return True


def _lock_event_already_emitted(hostname: Optional[str], event: Optional[Dict[str, Any]]) -> bool:
    if not event:
        return False
    record_id = str(event.get("event_record_id") or "")
    event_id = str(event.get("event_id") or "")
    if not record_id:
        return False
    state = _load_workstation_state()
    current = state.get(_state_key(hostname)) or {}
    return (
        str(current.get("last_lock_event_record_id") or "") == record_id
        and str(current.get("last_lock_event_id") or "") == event_id
    )


def _remember_lock_event_emitted(hostname: Optional[str], event: Optional[Dict[str, Any]]) -> None:
    if not event:
        return
    record_id = str(event.get("event_record_id") or "")
    if not record_id:
        return
    state = _load_workstation_state()
    key = _state_key(hostname)
    current = state.get(key) if isinstance(state.get(key), dict) else {}
    current.update({
        "state": "locked",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_lock_event_id": str(event.get("event_id") or ""),
        "last_lock_event_record_id": record_id,
    })
    state[key] = current
    _save_workstation_state(state)


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
        kernel32 = ctypes.windll.kernel32
        DESKTOP_SWITCHDESKTOP = 0x0100
        desktop = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if not desktop:
            error_code = kernel32.GetLastError()
            if error_code == 5:
                diagnostics = collect_foreground_diagnostics()
                current_session_id = diagnostics.get("current_session_id")
                active_console_session_id = diagnostics.get("active_console_session_id")
                if (
                    current_session_id is not None
                    and current_session_id == active_console_session_id
                    and int(current_session_id) > 0
                ):
                    logger.info(
                        "Windows lock probe confirmed locked: OpenInputDesktop denied in active console session. diagnostics=%s",
                        diagnostics,
                    )
                    return True
            logger.info(
                "Windows lock probe inconclusive: OpenInputDesktop returned no handle error=%s; not emitting LockApp.",
                error_code,
            )
            return None
        try:
            return not bool(user32.SwitchDesktop(desktop))
        finally:
            user32.CloseDesktop(desktop)
    except Exception as exc:
        logger.debug("Could not determine Windows lock state from input desktop: %s", exc)
        return None


def _locked_activity_record(lock_event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    timestamp = (lock_event or {}).get("event_timestamp") or datetime.now().astimezone().isoformat()
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
        "lock_state_transition": True,
        "windows_event_id": (lock_event or {}).get("event_id"),
        "windows_event_record_id": (lock_event or {}).get("event_record_id"),
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
    if record.get("windows_locked") or _is_lock_app(record):
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
    username = _current_username()
    lock_event = _latest_confirmed_windows_lock_event(username) if locked is not False else None
    unlock_event = _latest_confirmed_windows_unlock_event(username) if locked is not False else None
    if locked is True or (locked is None and _lock_event_is_current(socket.gethostname(), lock_event, unlock_event)):
        record = _locked_activity_record(lock_event)
        previous_state = _current_workstation_state(record.get("hostname"))
        if _apply_workstation_state(record.get("hostname"), True):
            _remember_lock_event_emitted(record.get("hostname"), lock_event)
            return record
        if (
            previous_state is None
            and lock_event
            and not _lock_event_already_emitted(record.get("hostname"), lock_event)
        ):
            logger.info(
                "Confirmed Windows lock event emitted to active application timeline: event_id=%s record_id=%s",
                lock_event.get("event_id"),
                lock_event.get("event_record_id"),
            )
            _remember_lock_event_emitted(record.get("hostname"), lock_event)
            return record
        logger.debug("Workstation remains locked; no duplicate LockApp active-application event emitted.")
        return None

    activity = collect_current_active_path()
    executable_name = activity.get("active_process_name")
    window_title = activity.get("active_window_title")

    if not executable_name and not window_title:
        return None

    application_name = executable_name.rsplit(".", 1)[0] if executable_name else "Unknown"
    timestamp = datetime.now().astimezone().isoformat()
    process_path = activity.get("active_process_path")
    idle_seconds = get_user_idle_seconds()

    record = {
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
        "windows_locked": False,
    }
    if locked is False:
        _apply_workstation_state(record.get("hostname"), False)
    return record


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
        record.get("application"),
        record.get("executable_name"),
        record.get("window_title"),
        record.get("process_path"),
    ]
    return any("lockapp" in str(value or "").lower() for value in values)


def _record_unlock_fallback_if_needed(record: Optional[Dict[str, Any]]) -> None:
    """
    Track LockApp observations without creating session records.

    Login Activity must only be driven by real Windows authentication/session
    events. Foreground LockApp transitions are useful for activity state, but
    they are not a durable authentication signal and must never create LOGIN
    rows.
    """
    global _lock_screen_observed, _last_lock_fallback_at, _last_unlock_fallback_at

    if _is_lock_app(record):
        if not _lock_screen_observed:
            logger.info("LockApp observed; waiting for Windows Event Log lock/unlock records.")
            _last_lock_fallback_at = time.time()
        _lock_screen_observed = True
        return

    if not _lock_screen_observed or not record:
        return

    now = time.time()
    if now - _last_unlock_fallback_at < UNLOCK_FALLBACK_DEBOUNCE_SECONDS:
        _lock_screen_observed = False
        return

    logger.info(
        "LockApp transition observed to %s; no Login Activity row created without a Windows unlock event.",
        record.get("application_name") or record.get("executable_name") or record.get("window_title"),
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
