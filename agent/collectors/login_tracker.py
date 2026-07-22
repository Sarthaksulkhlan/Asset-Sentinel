from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
for path in [
    ROOT_DIR,
    ROOT_DIR / "backend" / "api",
    ROOT_DIR / "backend" / "core",
    ROOT_DIR / "backend" / "models",
    ROOT_DIR / "backend" / "services",
    ROOT_DIR / "agent" / "collectors",
    ROOT_DIR / "agent" / "detectors",
    ROOT_DIR / "agent" / "windows",
    ROOT_DIR / "agent" / "client",
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
"""
Asset Sentinel Login Tracker
==============================
Detects Windows login events and records them to PostgreSQL.

This module:
1. Tracks current user sessions
2. Detects new logins by comparing with previous state
3. Records login details to PostgreSQL
4. Triggers login alerts to PostgreSQL
5. Maintains session state for logout detection

Design:
- Reads PostgreSQL sessions to find previous login records
- Compares with current session (via session_manager)
- Records new login if username/session_id changed
- Logs events for audit trail

For Windows Service deployment:
- Can be called repeatedly from a scheduler (Task Scheduler, Intune)
- Stateless design - state is stored in JSON files
- Enterprise-ready with comprehensive logging

Requires: session_manager, pywin32 (for Session ID)
"""

import json
import logging
import socket
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from session_manager import get_current_session_info
from api_client import (
    activate_session_event,
    has_session_event_signature,
    list_active_applications_history,
    list_alerts,
    list_sessions,
    replace_sessions,
    send_alert,
    send_session,
    touch_active_session,
)

COUNTABLE_LOGIN_SOURCES = {
    "windows_interactive_logon",
    "windows_unlock",
    "windows_session_reconnect",
    "windows_session_logon",
    "windows_session_unlock",
}
COUNTABLE_LOGIN_EVENT_IDS = {"4624", "4801", "4778", "WTS_SESSION_LOGON", "WTS_SESSION_UNLOCK"}
SESSION_STATE_SOURCES = {
    "windows_lock",
    "windows_session_disconnect",
}

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger("login_tracker")
SESSION_STATE_PATH = ROOT_DIR / "logs" / "session_event_state.json"


def _load_login_state() -> Dict[str, Any]:
    try:
        if SESSION_STATE_PATH.exists():
            with SESSION_STATE_PATH.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
                return state if isinstance(state, dict) else {}
    except Exception as exc:
        logger.warning("Could not read login state file %s: %s", SESSION_STATE_PATH, exc)
    return {}


def _save_login_state(state: Dict[str, Any]) -> None:
    try:
        SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SESSION_STATE_PATH.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
    except Exception as exc:
        logger.warning("Could not persist login state file %s: %s", SESSION_STATE_PATH, exc)


def _record_number(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    text = str(value)
    if ":" in text:
        text = text.rsplit(":", 1)[-1]
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _event_state_key(hostname: Optional[str]) -> str:
    return hostname or socket.gethostname() or "Unknown"


def _event_log_name(event_id: Optional[str]) -> str:
    event_text = str(event_id or "unknown").strip() or "unknown"
    return f"security:{event_text}"


def _is_event_already_processed(hostname: Optional[str], event_id: Optional[str], record_id: Optional[str]) -> bool:
    record_number = _record_number(record_id)
    if record_number is None:
        return False
    state = _load_login_state()
    host_state = state.get(_event_state_key(hostname), {})
    last_processed = _record_number(host_state.get(_event_log_name(event_id)))
    return bool(last_processed is not None and record_number <= last_processed)


def _mark_event_processed(hostname: Optional[str], event_id: Optional[str], record_id: Optional[str]) -> None:
    record_number = _record_number(record_id)
    if record_number is None:
        return
    state = _load_login_state()
    key = _event_state_key(hostname)
    host_state = state.setdefault(key, {})
    log_name = _event_log_name(event_id)
    previous = _record_number(host_state.get(log_name))
    if previous is None or record_number > previous:
        host_state[log_name] = record_number
        host_state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save_login_state(state)


# ============================================================================
# Session File Operations
# ============================================================================

def load_sessions() -> List[Dict[str, Any]]:
    """
    Load all login/logout records from PostgreSQL.
    
    Returns:
        list: Array of session records, empty list if none exist
    """
    try:
        return list_sessions()
    except Exception as e:
        logger.error(f"Error reading sessions from PostgreSQL: {e}")
        return []


def save_sessions(sessions: List[Dict[str, Any]]) -> bool:
    """
    Save session records to PostgreSQL.
    
    Args:
        sessions: List of session records
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        replace_sessions(sessions)
        logger.info(f"Saved {len(sessions)} session records to PostgreSQL")
        return True
    except Exception as e:
        logger.error(f"Failed to write sessions to PostgreSQL: {e}")
        return False


# ============================================================================
# Alert Integration (enterprise pattern)
# ============================================================================

def load_alerts() -> List[Dict[str, Any]]:
    """
    Load existing alerts from PostgreSQL.
    Reuses the alert system from motherboard_change_detector.py pattern.
    
    Returns:
        list: Array of alert records
    """
    try:
        return list_alerts()
    except Exception as e:
        logger.warning(f"Could not read alerts from PostgreSQL: {e}")
        return []


def save_alert(alert_type: str, hostname: str, severity: str, details: Dict[str, Any]) -> bool:
    """
    Record an alert to PostgreSQL.
    
    Follows the same pattern as existing detectors (motherboard_change_detector, etc.)
    
    Args:
        alert_type: e.g. "LOGIN", "LOGOUT"
        hostname: Machine hostname
        severity: "LOW", "MEDIUM", "HIGH", "CRITICAL"
        details: Dict with alert-specific data
        
    Returns:
        bool: True if alert saved successfully
    """
    try:
        send_alert(alert_type, hostname, severity, details, datetime.now(timezone.utc).isoformat())
        logger.info(f"Alert saved: {alert_type} for {hostname}")
        return True
    except Exception as e:
        logger.error(f"Failed to write alert to PostgreSQL: {e}")
        return False


# ============================================================================
# Login Detection Logic
# ============================================================================

def get_last_recorded_session() -> Optional[Dict[str, Any]]:
    """
    Get the most recent session record.
    
    Returns:
        dict: Last session record, or None if no sessions recorded yet
    """
    sessions = load_sessions()
    if not sessions:
        return None
    return sessions[-1]


def _is_countable_login_record(session: Dict[str, Any]) -> bool:
    if session.get("event_type") != "LOGIN":
        return False
    return (
        session.get("login_source") in COUNTABLE_LOGIN_SOURCES
        or str(session.get("windows_event_id") or "") in COUNTABLE_LOGIN_EVENT_IDS
    )


def get_last_countable_login_session() -> Optional[Dict[str, Any]]:
    for session in reversed(load_sessions()):
        if _is_countable_login_record(session):
            return session
    return None


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _format_duration(start_value: Optional[str], end_value: Optional[str]) -> str:
    start = _parse_iso_timestamp(start_value)
    end = _parse_iso_timestamp(end_value)
    if not start or not end:
        return "Unknown"
    seconds = max(0, int((end - start).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def _current_boot_time() -> Optional[datetime]:
    try:
        import psutil

        return datetime.fromtimestamp(psutil.boot_time(), timezone.utc)
    except Exception as exc:
        logger.warning("Could not read psutil.boot_time for stale session cleanup: %s", exc)
        return None


def close_stale_sessions_from_previous_boot(hostname: Optional[str] = None) -> int:
    boot_time = _current_boot_time()
    if boot_time is None:
        return 0

    sessions = load_sessions()
    closed = 0
    for session in sessions:
        if session.get("event_type") != "LOGIN" or session.get("active") is False:
            continue
        if hostname and session.get("hostname") != hostname:
            continue
        session_start = _parse_iso_timestamp(session.get("login_timestamp") or session.get("recorded_at"))
        if not session_start or session_start >= boot_time:
            continue
        session["logout_timestamp"] = boot_time.isoformat()
        session["session_duration"] = _format_duration(session.get("login_timestamp"), boot_time.isoformat())
        session["active"] = False
        session["device_status"] = None
        session["last_seen"] = boot_time.isoformat()
        closed += 1

    if closed:
        save_sessions(sessions)
        logger.info(
            "Closed stale active sessions from previous boot: hostname=%s boot_time=%s count=%s",
            hostname or "*",
            boot_time.isoformat(),
            closed,
        )
    return closed


def _record_observed_session_login(session_info: Dict[str, Any], reason: str) -> Optional[Dict[str, Any]]:
    hostname = session_info.get("hostname") or socket.gethostname()
    logger.info(
        "Observed Windows session ignored: reason=%s host=%s user=%s session=%s. "
        "Login rows require a real Windows authentication Event Record ID.",
        reason,
        hostname,
        session_info.get("username"),
        session_info.get("session_id"),
    )
    return None


def record_windows_session_notification(
    event_id: str,
    session_id: Optional[str],
    event_timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a genuine Windows service session logon/unlock notification."""
    if event_id not in {"WTS_SESSION_LOGON", "WTS_SESSION_UNLOCK"}:
        return {}
    session_info = get_current_session_info()
    current_session_id = str(session_info.get("session_id") or "")
    notified_session_id = str(session_id or "")
    if notified_session_id and current_session_id and notified_session_id != current_session_id:
        logger.info(
            "Windows session notification ignored for non-console session: event=%s notified=%s current=%s",
            event_id,
            notified_session_id,
            current_session_id,
        )
        return {}
    timestamp = event_timestamp or datetime.now(timezone.utc).isoformat()
    record_number = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    record_id = f"{event_id.lower()}:{session_info.get('hostname') or socket.gethostname()}:{notified_session_id or current_session_id}:{record_number}"
    if has_session_event_signature(session_info.get("hostname"), record_id):
        return {}
    return record_login({
        **session_info,
        "session_id": notified_session_id or current_session_id or session_info.get("session_id"),
        "login_timestamp": timestamp,
        "login_source": "windows_session_unlock" if event_id == "WTS_SESSION_UNLOCK" else "windows_session_logon",
        "windows_event_id": event_id,
        "windows_event_record_id": record_id,
    })


def _record_lockapp_unlocks_from_history(
    current_session: Dict[str, Any],
    last_session: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    logger.debug("LockApp active-application history is not used for login detection.")
    return None


def record_session_state_event(
    session_info: Dict[str, Any],
    state: str,
    timestamp: str,
    source: str,
    event_id: str,
    record_id: Optional[str],
) -> Dict[str, Any]:
    hostname = session_info.get("hostname") or socket.gethostname()
    if record_id and has_session_event_signature(hostname, record_id):
        return {}
    event_type = "LOGOUT" if state == "LOCK" else "LOGIN"
    record = {
        "event_type": event_type,
        "username": session_info.get("username"),
        "hostname": hostname,
        "ip_address": session_info.get("ip_address"),
        "session_id": session_info.get("session_id"),
        "login_timestamp": timestamp if event_type == "LOGIN" else session_info.get("login_timestamp"),
        "logout_timestamp": timestamp if event_type == "LOGOUT" else None,
        "session_duration": state.title(),
        "active": False,
        "device_status": None,
        "last_seen": timestamp,
        "login_source": source,
        "windows_event_id": event_id,
        "windows_event_record_id": record_id,
        "recorded_at": timestamp,
    }
    send_session(record)
    return record


def close_active_sessions(
    sessions: List[Dict[str, Any]],
    current_session: Dict[str, Any],
    logout_timestamp: str,
) -> List[Dict[str, Any]]:
    """
    Mark previous active sessions as logged out.

    The dashboard reads these fields directly:
    - logout_timestamp
    - session_duration
    - active
    - device_status
    """
    current_user = current_session.get("username")
    current_session_id = current_session.get("session_id")
    force_close = bool(current_session.get("force_close_active_sessions"))
    logout_event_record_id = current_session.get("latest_logout_event_record_id")
    logout_event_id = current_session.get("latest_logout_event_id") or "4634"
    logout_source = "windows_logoff"
    if logout_event_id == "4800":
        logout_source = "windows_lock"
    elif logout_event_id == "4779":
        logout_source = "windows_session_disconnect"
    logout_records: List[Dict[str, Any]] = []

    for session in sessions:
        if session.get("event_type") != "LOGIN" or session.get("active") is False:
            continue

        same_session = (
            session.get("username") == current_user and
            session.get("session_id") == current_session_id
        )
        if same_session and not force_close:
            continue

        session["logout_timestamp"] = logout_timestamp
        session["session_duration"] = _format_duration(session.get("login_timestamp"), logout_timestamp)
        session["active"] = False
        session["device_status"] = None
        session["last_seen"] = logout_timestamp

        logout_records.append({
            "event_type": "LOGOUT",
            "username": session.get("username"),
            "hostname": session.get("hostname"),
            "ip_address": session.get("ip_address"),
            "session_id": session.get("session_id"),
            "login_timestamp": session.get("login_timestamp"),
            "logout_timestamp": logout_timestamp,
            "session_duration": session.get("session_duration"),
            "active": False,
            "device_status": None,
            "last_seen": logout_timestamp,
            "login_source": logout_source,
            "windows_event_id": logout_event_id,
            "windows_event_record_id": logout_event_record_id,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(
            "Logout detected: user=%s host=%s session=%s event_id=%s record_id=%s",
            session.get("username"),
            session.get("hostname"),
            session.get("session_id"),
            logout_event_id,
            logout_event_record_id,
        )

        save_alert(
            alert_type="LOGOUT",
            hostname=session.get("hostname"),
            severity="LOW",
            details={
                "username": session.get("username"),
                "ip_address": session.get("ip_address"),
                "session_id": session.get("session_id"),
                "logout_timestamp": logout_timestamp,
                "session_duration": session.get("session_duration"),
            }
        )

    sessions.extend(logout_records)
    return sessions


def detect_login() -> Optional[Dict[str, Any]]:
    """
    Detect if a new login has occurred.
    
    Logic:
    1. Get current session info
    2. Compare with last recorded session
    3. If username OR session_id changed, it's a new login
    4. Record the new login
    5. Create an alert
    
    Returns:
        dict: New login record if login detected, None otherwise
    """
    current_session = get_current_session_info()
    last_session = get_last_recorded_session()
    last_countable_session = get_last_countable_login_session()
    current_user = current_session.get("username")
    current_session_id = current_session.get("session_id")
    current_event_record_id = current_session.get("windows_event_record_id")

    logout_timestamp = (
        current_session.get("latest_logout_timestamp")
        or datetime.now(timezone.utc).isoformat()
    )
    logout_event_record_id = current_session.get("latest_logout_event_record_id")

    if not current_user:
        logger.info("No active Windows user detected - closing active sessions")
        sessions = load_sessions()
        updated_sessions = close_active_sessions(
            sessions,
            current_session,
            logout_timestamp
        )
        save_sessions(updated_sessions)
        return None

    lockapp_login = _record_lockapp_unlocks_from_history(current_session, last_session)
    if lockapp_login:
        return lockapp_login

    unlock_event_record_id = current_session.get("latest_unlock_event_record_id")
    if (
        unlock_event_record_id
        and not _is_event_already_processed(
            current_session.get("hostname"),
            current_session.get("latest_unlock_event_id"),
            unlock_event_record_id,
        )
        and not has_session_event_signature(current_session.get("hostname"), unlock_event_record_id)
    ):
        unlock_session = {
            **current_session,
            "login_timestamp": current_session.get("latest_unlock_timestamp") or datetime.now(timezone.utc).isoformat(),
            "login_source": "windows_unlock" if current_session.get("latest_unlock_event_id") == "4801" else "windows_session_reconnect",
            "windows_event_id": current_session.get("latest_unlock_event_id") or "4801",
            "windows_event_record_id": unlock_event_record_id,
        }
        logger.info(
            "Windows unlock detected as new current session: host=%s user=%s event_id=%s record_id=%s",
            unlock_session.get("hostname"),
            unlock_session.get("username"),
            unlock_session.get("windows_event_id"),
            unlock_event_record_id,
        )
        return record_login(unlock_session)
    if unlock_event_record_id:
        _mark_event_processed(
            current_session.get("hostname"),
            current_session.get("latest_unlock_event_id"),
            unlock_event_record_id,
        )

    if (
        logout_event_record_id
        and current_session.get("latest_logout_event_id") in {"4800", "4779"}
        and not _is_event_already_processed(
            current_session.get("hostname"),
            current_session.get("latest_logout_event_id"),
            logout_event_record_id,
        )
        and not has_session_event_signature(current_session.get("hostname"), logout_event_record_id)
    ):
        lock_session = {
            **current_session,
            "force_close_active_sessions": True,
            "latest_logout_timestamp": logout_timestamp,
            "latest_logout_event_id": current_session.get("latest_logout_event_id") or "4800",
            "latest_logout_event_record_id": logout_event_record_id,
        }
        sessions = load_sessions()
        before_count = len(sessions)
        updated_sessions = close_active_sessions(sessions, lock_session, logout_timestamp)
        if len(updated_sessions) != before_count or any(
            session.get("active") is False and session.get("logout_timestamp") == logout_timestamp
            for session in updated_sessions
        ):
            save_sessions(updated_sessions)
        logger.info(
            "Windows lock event %s record %s closed current session",
            current_session.get("latest_logout_event_id"),
            logout_event_record_id,
        )
        _mark_event_processed(
            current_session.get("hostname"),
            current_session.get("latest_logout_event_id"),
            logout_event_record_id,
        )
        return None
    elif (
        logout_event_record_id
        and not _is_event_already_processed(
            current_session.get("hostname"),
            current_session.get("latest_logout_event_id"),
            logout_event_record_id,
        )
        and not has_session_event_signature(current_session.get("hostname"), logout_event_record_id)
    ):
        sessions = load_sessions()
        before_count = len(sessions)
        updated_sessions = close_active_sessions(sessions, current_session, logout_timestamp)
        if len(updated_sessions) != before_count:
            logger.info(
                "Windows logoff event 4634 record %s closed stale sessions",
                logout_event_record_id,
            )
            save_sessions(updated_sessions)
        _mark_event_processed(
            current_session.get("hostname"),
            current_session.get("latest_logout_event_id"),
            logout_event_record_id,
        )
    elif logout_event_record_id:
        _mark_event_processed(
            current_session.get("hostname"),
            current_session.get("latest_logout_event_id"),
            logout_event_record_id,
        )
    
    # First run - no previous session
    comparison_session = last_countable_session or last_session

    if comparison_session is None:
        if (
            current_event_record_id
            and current_session.get("login_source") in COUNTABLE_LOGIN_SOURCES
            and not _is_event_already_processed(
                current_session.get("hostname"),
                current_session.get("windows_event_id"),
                current_event_record_id,
            )
        ):
            logger.info(
                "First run detected with real Windows login event %s record %s",
                current_session.get("windows_event_id"),
                current_event_record_id,
            )
            return record_login(current_session)
        if current_event_record_id:
            _mark_event_processed(
                current_session.get("hostname"),
                current_session.get("windows_event_id"),
                current_event_record_id,
            )
        logger.info(
            "First run detected without a new Security log authentication event; no login row will be created."
        )
        return None
    
    # Check if user or session changed (indicates logout/login)
    last_user = comparison_session.get("username")
    last_session_id = comparison_session.get("session_id")
    last_event_record_id = comparison_session.get("windows_event_record_id")
    last_hostname = comparison_session.get("hostname")
    current_hostname = current_session.get("hostname")

    if current_hostname and current_hostname != last_hostname:
        logger.info(
            "Hostname changed from %s to %s; using observed interactive session fallback",
            last_hostname,
            current_hostname,
        )
        return _record_observed_session_login(current_session, "hostname_changed")

    if current_event_record_id and current_event_record_id != last_event_record_id:
        if (
            current_session.get("login_source") not in SESSION_STATE_SOURCES
            and not _is_event_already_processed(
                current_session.get("hostname"),
                current_session.get("windows_event_id"),
                current_event_record_id,
            )
            and not has_session_event_signature(current_session.get("hostname"), current_event_record_id)
        ):
            logger.info(
                "Login detected from Windows event %s record %s",
                current_session.get("windows_event_id"),
                current_event_record_id,
            )
            return record_login(current_session)
        _mark_event_processed(
            current_session.get("hostname"),
            current_session.get("windows_event_id"),
            current_event_record_id,
        )
    
    # Different username = new login
    if current_user != last_user:
        logger.info("User changed without Security log event; using observed interactive session fallback.")
        return _record_observed_session_login(current_session, "user_changed_without_security_event")
    
    # Different session ID with same user = new login
    if current_session_id != last_session_id and current_user == last_user:
        logger.info("Session ID changed without Security log event; using observed interactive session fallback.")
        return _record_observed_session_login(current_session, "session_changed_without_security_event")

    if current_session.get("login_source") == "session_poll":
        observed = _record_observed_session_login(current_session, "security_event_unavailable")
        if observed:
            return observed
    
    # No login detected
    touch_active_session(
        current_session.get("hostname"),
        current_session.get("username"),
        current_session.get("session_id"),
    )
    logger.debug(f"No login detected - user {current_user} still in session {current_session_id}")
    return None


def record_login(session_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record a login event to PostgreSQL and create an alert.
    
    Args:
        session_info: Dictionary from get_current_session_info()
        
    Returns:
        dict: The login record that was saved
    """
    sessions = load_sessions()
    now = datetime.now(timezone.utc).isoformat()
    event_record_id = session_info.get("windows_event_record_id")
    hostname = session_info.get("hostname")
    if event_record_id and has_session_event_signature(hostname, event_record_id):
        logger.info("Skipping duplicate Windows login event record %s for %s", event_record_id, hostname)
        _mark_event_processed(hostname, session_info.get("windows_event_id"), event_record_id)
        if (
            session_info.get("login_source") in COUNTABLE_LOGIN_SOURCES
            or str(session_info.get("windows_event_id") or "") in COUNTABLE_LOGIN_EVENT_IDS
        ):
            activate_session_event(hostname, event_record_id, now)
        touch_active_session(hostname, session_info.get("username"), session_info.get("session_id"))
        return {}
    if (
        session_info.get("login_source") not in COUNTABLE_LOGIN_SOURCES
        and str(session_info.get("windows_event_id") or "") not in COUNTABLE_LOGIN_EVENT_IDS
    ):
        logger.info(
            "Skipping non-countable login source: host=%s source=%s event=%s",
            hostname,
            session_info.get("login_source"),
            session_info.get("windows_event_id"),
        )
        return {}
    session_info = {**session_info, "force_close_active_sessions": True}
    login_time = _parse_iso_timestamp(session_info.get("login_timestamp"))
    latest_logout_time = _parse_iso_timestamp(session_info.get("latest_logout_timestamp"))
    close_timestamp = (
        session_info.get("latest_logout_timestamp")
        if latest_logout_time and (login_time is None or latest_logout_time <= login_time)
        else now
    )
    sessions = close_active_sessions(sessions, session_info, close_timestamp)

    # Create login record
    login_record = {
        "event_type": "LOGIN",
        "username": session_info.get("username"),
        "hostname": session_info.get("hostname"),
        "ip_address": session_info.get("ip_address"),
        "session_id": session_info.get("session_id"),
        "login_timestamp": session_info.get("login_timestamp"),
        "logout_timestamp": None,
        "session_duration": "Active",
        "active": True,
        "device_status": None,
        "last_seen": now,
        "login_source": session_info.get("login_source"),
        "windows_event_id": session_info.get("windows_event_id"),
        "windows_event_record_id": session_info.get("windows_event_record_id"),
        "recorded_at": now,
    }
    
    if not save_sessions(sessions):
        logger.warning("Closed session updates were not persisted before login insert; continuing with login event insert: %s", login_record)

    try:
        send_session(login_record)
        _mark_event_processed(hostname, session_info.get("windows_event_id"), event_record_id)
    except Exception as exc:
        logger.exception("Login record insert failed in PostgreSQL: %s", exc)
        return login_record
    
    # Create alert for this login
    alert_details = {
        "username": login_record.get("username"),
        "ip_address": login_record.get("ip_address"),
        "session_id": login_record.get("session_id"),
        "login_timestamp": login_record.get("login_timestamp"),
        "login_source": login_record.get("login_source"),
        "windows_event_id": login_record.get("windows_event_id"),
        "windows_event_record_id": login_record.get("windows_event_record_id"),
    }
    
    save_alert(
        alert_type="LOGIN",
        hostname=login_record.get("hostname"),
        severity="MEDIUM",  # Login events are MEDIUM severity
        details=alert_details
    )
    
    logger.info(
        "Login detected and recorded: user=%s host=%s session=%s event_id=%s record_id=%s",
        login_record.get("username"),
        login_record.get("hostname"),
        login_record.get("session_id"),
        login_record.get("windows_event_id"),
        login_record.get("windows_event_record_id"),
    )
    
    return login_record


# ============================================================================
# CLI / Entry Point (for Task Scheduler)
# ============================================================================

def main():
    """
    Main entry point - can be called from Windows Task Scheduler.
    
    This function:
    1. Detects if a login occurred
    2. Records it if necessary
    3. Exits cleanly for scheduling
    
    For Windows Service deployment:
    - Call this function periodically (e.g., every 5 minutes)
    - Or integrate into an event-based system
    """
    logger.info("=" * 70)
    logger.info("Asset Sentinel Login Tracker - Starting")
    logger.info("=" * 70)
    
    current_session = get_current_session_info()
    logger.info(f"Current session: {current_session.get('username')} "
                f"on {current_session.get('hostname')}")
    
    new_login = detect_login()
    
    if new_login:
        logger.info(f"??? New login recorded: {new_login.get('username')}")
    else:
        logger.info("No new login detected")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    main()

