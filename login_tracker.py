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
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from session_manager import get_current_session_info
from storage import append_alert, list_alerts, list_sessions, replace_sessions, touch_active_session, update_asset_heartbeat

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger("login_tracker")


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
        append_alert(
            alert_type=alert_type,
            hostname=hostname,
            severity=severity,
            details=details,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
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

    for session in sessions:
        if session.get("event_type") != "LOGIN" or session.get("active") is False:
            continue

        same_session = (
            session.get("username") == current_user and
            session.get("session_id") == current_session_id
        )
        if same_session:
            continue

        session["logout_timestamp"] = logout_timestamp
        session["session_duration"] = _format_duration(session.get("login_timestamp"), logout_timestamp)
        session["active"] = False
        session["device_status"] = "Offline"
        session["last_seen"] = logout_timestamp

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
    current_user = current_session.get("username")

    if not current_user:
        logger.info("No active Windows user detected - closing active sessions")
        sessions = load_sessions()
        updated_sessions = close_active_sessions(
            sessions,
            current_session,
            datetime.now(timezone.utc).isoformat()
        )
        save_sessions(updated_sessions)
        return None
    
    # First run - no previous session
    if last_session is None:
        logger.info("First run detected - recording initial login")
        return record_login(current_session)
    
    # Check if user or session changed (indicates logout/login)
    current_session_id = current_session.get("session_id")
    
    last_user = last_session.get("username")
    last_session_id = last_session.get("session_id")
    
    # Different username = new login
    if current_user != last_user:
        logger.info(f"Login detected: user changed from {last_user} to {current_user}")
        return record_login(current_session)
    
    # Different session ID with same user = new login
    if current_session_id != last_session_id and current_user == last_user:
        logger.info(f"Login detected: session ID changed from {last_session_id} to {current_session_id}")
        return record_login(current_session)
    
    # No login detected
    touch_active_session(
        current_session.get("hostname"),
        current_session.get("username"),
        current_session.get("session_id"),
    )
    update_asset_heartbeat(current_session.get("hostname"))
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
    sessions = close_active_sessions(sessions, session_info, now)

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
        "device_status": "Online",
        "last_seen": now,
        "recorded_at": now,
    }
    
    # Append to PostgreSQL
    sessions.append(login_record)
    save_sessions(sessions)
    
    # Create alert for this login
    alert_details = {
        "username": login_record.get("username"),
        "ip_address": login_record.get("ip_address"),
        "session_id": login_record.get("session_id"),
        "login_timestamp": login_record.get("login_timestamp"),
    }
    
    save_alert(
        alert_type="LOGIN",
        hostname=login_record.get("hostname"),
        severity="MEDIUM",  # Login events are MEDIUM severity
        details=alert_details
    )
    
    logger.info(f"Login recorded: {login_record.get('username')} on {login_record.get('hostname')}")
    update_asset_heartbeat(login_record.get("hostname"))
    
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
        logger.info(f"✓ New login recorded: {new_login.get('username')}")
    else:
        logger.info("No new login detected")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
