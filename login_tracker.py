"""
Asset Sentinel Login Tracker
==============================
Detects Windows login events and records them to sessions.json.

This module:
1. Tracks current user sessions
2. Detects new logins by comparing with previous state
3. Records login details to sessions.json
4. Triggers login alerts to alerts.json
5. Maintains session state for logout detection

Design:
- Reads sessions.json to find previous login records
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
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from session_manager import get_current_session_info

# ============================================================================
# Configuration
# ============================================================================

SESSIONS_FILE = Path("sessions.json")
ALERTS_FILE = Path("alerts.json")

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
    Load all login/logout records from sessions.json.
    
    Returns:
        list: Array of session records, empty list if file doesn't exist
    """
    if not SESSIONS_FILE.exists():
        logger.info("sessions.json does not exist yet - starting fresh")
        return []
    
    try:
        content = SESSIONS_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse sessions.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading sessions.json: {e}")
        return []


def save_sessions(sessions: List[Dict[str, Any]]) -> bool:
    """
    Save session records to sessions.json.
    
    Args:
        sessions: List of session records
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        SESSIONS_FILE.write_text(
            json.dumps(sessions, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(sessions)} session records to sessions.json")
        return True
    except Exception as e:
        logger.error(f"Failed to write sessions.json: {e}")
        return False


# ============================================================================
# Alert Integration (enterprise pattern)
# ============================================================================

def load_alerts() -> List[Dict[str, Any]]:
    """
    Load existing alerts from alerts.json.
    Reuses the alert system from motherboard_change_detector.py pattern.
    
    Returns:
        list: Array of alert records
    """
    if not ALERTS_FILE.exists():
        return []
    
    try:
        content = ALERTS_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Could not read alerts.json: {e}")
        return []


def save_alert(alert_type: str, hostname: str, severity: str, details: Dict[str, Any]) -> bool:
    """
    Record an alert to alerts.json.
    
    Follows the same pattern as existing detectors (motherboard_change_detector, etc.)
    
    Args:
        alert_type: e.g. "LOGIN", "LOGOUT"
        hostname: Machine hostname
        severity: "LOW", "MEDIUM", "HIGH", "CRITICAL"
        details: Dict with alert-specific data
        
    Returns:
        bool: True if alert saved successfully
    """
    alerts = load_alerts()
    
    record = {
        "alert_type": alert_type,
        "hostname": hostname,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }
    
    alerts.append(record)
    
    try:
        ALERTS_FILE.write_text(
            json.dumps(alerts, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Alert saved: {alert_type} for {hostname}")
        return True
    except Exception as e:
        logger.error(f"Failed to write alerts.json: {e}")
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
    
    # First run - no previous session
    if last_session is None:
        logger.info("First run detected - recording initial login")
        return record_login(current_session)
    
    # Check if user or session changed (indicates logout/login)
    current_user = current_session.get("username")
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
    logger.debug(f"No login detected - user {current_user} still in session {current_session_id}")
    return None


def record_login(session_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Record a login event to sessions.json and create an alert.
    
    Args:
        session_info: Dictionary from get_current_session_info()
        
    Returns:
        dict: The login record that was saved
    """
    # Create login record
    login_record = {
        "event_type": "LOGIN",
        "username": session_info.get("username"),
        "hostname": session_info.get("hostname"),
        "ip_address": session_info.get("ip_address"),
        "session_id": session_info.get("session_id"),
        "login_timestamp": session_info.get("login_timestamp"),
        "device_status": "Online",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Append to sessions.json
    sessions = load_sessions()
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
