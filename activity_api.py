"""
Asset Sentinel Activity API Routes
===================================
REST API endpoints for session and login tracking.

Provides endpoints that your dashboard will consume:
- GET /current-user - Current logged-in user info
- GET /current-session - Current session details
- GET /device-status - Device online/offline status
- GET /sessions - History of all logins

This module is imported by app.py and routes are registered there.

Design:
- Blueprint-style functions for Flask integration
- JSON responses matching enterprise standards
- Error handling with proper HTTP status codes
- No data modification (read-only)

For future Intune/Azure integration:
- Responses are formatted for cloud API compatibility
- Timestamps are in ISO 8601 format
- All data is JSON-serializable

Usage in app.py:
    from activity_api import get_current_user, get_current_session, etc.
    
    @app.route("/current-user", methods=["GET"])
    def current_user():
        return get_current_user()
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

from session_manager import get_current_session_info, get_device_status
from login_tracker import load_sessions

# ============================================================================
# Configuration
# ============================================================================

SESSIONS_FILE = Path("sessions.json")

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger("activity_api")


# ============================================================================
# API Response Functions (return dicts - Flask app.py handles jsonify)
# ============================================================================

def get_current_user() -> Tuple[Dict[str, Any], int]:
    """
    GET /current-user
    
    Returns the currently logged-in user information.
    
    Response:
        {
            "username": "Victus",
            "hostname": "AI",
            "device_status": "Online"
        }
        
    Status: 200 OK on success
    """
    try:
        session_info = get_current_session_info()
        response = {
            "username": session_info.get("username"),
            "hostname": session_info.get("hostname"),
            "device_status": session_info.get("device_status"),
        }
        logger.info(f"GET /current-user: {response.get('username')} on {response.get('hostname')}")
        return response, 200
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}")
        return {"error": "Failed to retrieve current user"}, 500


def get_current_session() -> Tuple[Dict[str, Any], int]:
    """
    GET /current-session
    
    Returns comprehensive current session information.
    Includes all session tracking data.
    
    Response:
        {
            "username": "Victus",
            "hostname": "AI",
            "ip_address": "192.168.1.148",
            "session_id": "1",
            "login_timestamp": "2026-06-17T09:40:03.842041+00:00",
            "device_status": "Online",
            "collection_timestamp": "2026-06-17T09:40:03.842041+00:00"
        }
        
    Status: 200 OK on success
    """
    try:
        session_info = get_current_session_info()
        logger.info(f"GET /current-session: {session_info.get('username')}")
        return session_info, 200
    except Exception as e:
        logger.error(f"Error in get_current_session: {e}")
        return {"error": "Failed to retrieve current session"}, 500


def get_device_status_endpoint() -> Tuple[Dict[str, Any], int]:
    """
    GET /device-status
    
    Returns device online/offline status.
    
    Response:
        {
            "device_status": "Online",
            "hostname": "AI",
            "last_activity": "2026-06-17T09:40:03.842041+00:00"
        }
        
    Status: 200 OK on success
    """
    try:
        session_info = get_current_session_info()
        device_status = session_info.get("device_status")
        response = {
            "device_status": device_status,
            "hostname": session_info.get("hostname"),
            "last_activity": session_info.get("collection_timestamp"),
        }
        logger.info(f"GET /device-status: {device_status}")
        return response, 200
    except Exception as e:
        logger.error(f"Error in get_device_status_endpoint: {e}")
        return {"error": "Failed to retrieve device status"}, 500


def get_sessions_history() -> Tuple[List[Dict[str, Any]], int]:
    """
    GET /sessions
    
    Returns all login/logout events history.
    Returns array of all session events in chronological order.
    
    Response:
        [
            {
                "event_type": "LOGIN",
                "username": "Victus",
                "hostname": "AI",
                "ip_address": "192.168.1.148",
                "session_id": "1",
                "login_timestamp": "2026-06-17T09:40:03.842041+00:00",
                "device_status": "Online",
                "recorded_at": "2026-06-17T09:40:03.842041+00:00"
            }
        ]
        
    Status: 200 OK on success (empty array if no sessions)
    """
    try:
        sessions = load_sessions()
        logger.info(f"GET /sessions: returning {len(sessions)} records")
        return sessions, 200
    except Exception as e:
        logger.error(f"Error in get_sessions_history: {e}")
        return {"error": "Failed to retrieve sessions"}, 500


# ============================================================================
# Additional Helper Endpoints (future features)
# ============================================================================

def get_sessions_count() -> Tuple[Dict[str, Any], int]:
    """
    GET /sessions/count
    
    Returns count of login/logout events.
    Useful for quick statistics.
    
    Response:
        {
            "total_sessions": 5,
            "total_logins": 5,
            "total_logouts": 2
        }
    """
    try:
        sessions = load_sessions()
        login_count = len([s for s in sessions if s.get("event_type") == "LOGIN"])
        logout_count = len([s for s in sessions if s.get("event_type") == "LOGOUT"])
        
        response = {
            "total_sessions": len(sessions),
            "total_logins": login_count,
            "total_logouts": logout_count,
        }
        logger.info(f"GET /sessions/count: {response}")
        return response, 200
    except Exception as e:
        logger.error(f"Error in get_sessions_count: {e}")
        return {"error": "Failed to retrieve sessions count"}, 500


# ============================================================================
# Entry Point for Testing
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  Asset Sentinel Activity API - Test Output")
    print("=" * 70 + "\n")
    
    data, status = get_current_user()
    print(f"GET /current-user (Status: {status}):")
    print(json.dumps(data, indent=2))
    
    data, status = get_current_session()
    print(f"\nGET /current-session (Status: {status}):")
    print(json.dumps(data, indent=2))
    
    data, status = get_device_status_endpoint()
    print(f"\nGET /device-status (Status: {status}):")
    print(json.dumps(data, indent=2))
    
    data, status = get_sessions_history()
    print(f"\nGET /sessions (Status: {status}):")
    print(json.dumps(data, indent=2))
    
    data, status = get_sessions_count()
    print(f"\nGET /sessions/count (Status: {status}):")
    print(json.dumps(data, indent=2))
    
    print("\n" + "=" * 70 + "\n")
