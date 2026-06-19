import json
import socket
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS
from collect_hardware import collect_current_active_path

# Import session tracking modules
from activity_api import (
    get_current_user,
    get_current_session,
    get_device_status_endpoint,
    get_sessions_history,
    get_sessions_count,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app)  # Allow requests from React / Lovable frontend on any origin

# File paths - both files must be in the same folder as app.py
ASSETS_FILE = Path("assets.json")
ALERTS_FILE = Path("alerts.json")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def read_json_file(file_path):
    """
    Read a JSON file and return its contents as a Python list.
    Returns an empty list if the file does not exist or is unreadable.
    """
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARNING] Could not read {file_path.name}: {e}")
        return []


def enrich_assets_with_current_activity(assets):
    """
    Add the live foreground activity to the current machine's asset record.
    This keeps the dashboard's current active path column populated while
    preserving the existing assets.json storage format.
    """
    if not assets:
        return assets

    try:
        current_hostname = socket.gethostname()
        activity = collect_current_active_path()
        current_activity = activity.get("active_process_path") or activity.get("current_website")
        if not current_activity:
            return assets

        enriched_assets = []
        for asset in assets:
            if asset.get("hostname") == current_hostname:
                enriched_assets.append({
                    **asset,
                    **activity,
                    "currentWebsite": current_activity,
                    "current_website": current_activity,
                    "current_active_path": current_activity,
                    "active_window": activity.get("active_window_title"),
                    "active_application": activity.get("active_process_name"),
                })
            else:
                enriched_assets.append(asset)
        return enriched_assets
    except Exception as e:
        print(f"[WARNING] Could not enrich current activity: {e}")
        return assets


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/assets", methods=["GET"])
def get_assets():
    """
    GET /api/assets
    Returns all hardware snapshots from assets.json.
    """
    assets = read_json_file(ASSETS_FILE)
    return jsonify(enrich_assets_with_current_activity(assets))


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """
    GET /api/alerts
    Returns all alert records from alerts.json.
    """
    alerts = read_json_file(ALERTS_FILE)
    return jsonify(alerts)


# ============================================================================
# Session Tracking APIs (Feature 1: Login Tracking)
# ============================================================================

@app.route("/current-user", methods=["GET"])
def current_user():
    """
    GET /current-user
    Returns the currently logged-in user information.
    
    Response:
        {
            "username": "Victus",
            "hostname": "AI",
            "device_status": "Online"
        }
    """
    data, status_code = get_current_user()
    return jsonify(data), status_code


@app.route("/current-session", methods=["GET"])
def current_session():
    """
    GET /current-session
    Returns comprehensive current session information.
    
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
    """
    data, status_code = get_current_session()
    return jsonify(data), status_code


@app.route("/device-status", methods=["GET"])
def device_status():
    """
    GET /device-status
    Returns device online/offline status.
    
    Response:
        {
            "device_status": "Online",
            "hostname": "AI",
            "last_activity": "2026-06-17T09:40:03.842041+00:00"
        }
    """
    data, status_code = get_device_status_endpoint()
    return jsonify(data), status_code


@app.route("/sessions", methods=["GET"])
@app.route("/api/sessions", methods=["GET"])
def sessions():
    """
    GET /sessions
    Returns all login/logout events history.
    
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
    """
    data, status_code = get_sessions_history()
    return jsonify(data), status_code


@app.route("/sessions/count", methods=["GET"])
@app.route("/api/sessions/count", methods=["GET"])
def sessions_count():
    """
    GET /sessions/count
    Returns count of login/logout events.
    
    Response:
        {
            "total_sessions": 1,
            "total_logins": 1,
            "total_logouts": 0
        }
    """
    data, status_code = get_sessions_count()
    return jsonify(data), status_code


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 70)
    print("  Asset Sentinel Backend")
    print("  Running on http://localhost:5000")
    print("=" * 70)
    print("  Hardware Monitoring APIs:")
    print("    GET /api/assets")
    print("    GET /api/alerts")
    print("=" * 70)
    print("  Session & Activity Tracking APIs (Feature 1):")
    print("    GET /current-user")
    print("    GET /current-session")
    print("    GET /device-status")
    print("    GET /sessions")
    print("    GET /sessions/count")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=True)
