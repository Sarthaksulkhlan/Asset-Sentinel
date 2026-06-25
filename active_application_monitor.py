import os
import socket
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from collect_hardware import collect_current_active_path
from storage import (
    append_active_application,
    get_latest_active_application_for_host as get_latest_active_application_for_host_from_db,
    get_latest_active_applications as get_latest_active_applications_from_db,
    list_active_applications_history,
    update_asset_heartbeat,
)


POLL_INTERVAL_SECONDS = 2

_monitor_lock = threading.Lock()
_monitor_started = False
_last_signature: Optional[tuple] = None


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
            if record:
                _append_if_changed(record)
        except Exception as exc:
            print(f"[WARNING] Active application monitor error: {exc}")
        time.sleep(POLL_INTERVAL_SECONDS)


def start_active_application_monitor() -> None:
    global _monitor_started, _last_signature

    with _monitor_lock:
        if _monitor_started:
            return
        history = _read_activity_history()
        if history:
            _last_signature = _record_signature(history[-1])
        _monitor_started = True

    thread = threading.Thread(target=_monitor_loop, name="active-application-monitor", daemon=True)
    thread.start()
    print("[INFO] Active application monitor started.")


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
