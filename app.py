import os
import socket
import sys
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from config import print_startup_environment_diagnostics
from collect_hardware import collect_current_active_path
from active_application_monitor import (
    get_latest_active_applications,
    get_latest_active_application_for_host,
    start_active_application_monitor,
    start_login_event_monitor,
)

# Import session tracking modules
from activity_api import (
    get_current_user,
    get_current_session,
    get_device_status_endpoint,
    get_sessions_history,
    get_sessions_count,
)
from database import init_db
from storage import get_asset_details, list_alerts, list_assets, normalize_active_application_timestamps
from registration import register_admin, submit_early_access
from telemetry_bootstrap import bootstrap_local_telemetry
from auth import (
    authenticate_local,
    bootstrap_admin_user,
    ensure_auth_schema,
    refresh_access_token,
    require_auth,
    revoke_refresh_token,
    serialize_user,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
CORS(app, supports_credentials=True, allow_headers=["Content-Type", "Authorization"])  # Allow React frontend auth headers


@app.after_request
def add_live_api_cache_headers(response):
    if request.path.startswith("/api/assets") or request.path == "/api/active-applications":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def enrich_assets_with_current_activity(assets):
    """
    Add the live foreground activity to the current machine's asset record.
    This keeps the dashboard's current active path column populated while
    preserving the existing API response format.
    """
    if not assets:
        return assets

    try:
        current_hostname = socket.gethostname()
        activity = collect_current_active_path()
        current_activity = activity.get("active_process_path") or activity.get("current_website")
        current_monitor_record = get_latest_active_application_for_host(current_hostname)
        if not current_activity:
            current_activity = (
                current_monitor_record.get("process_path")
                or current_monitor_record.get("executable_name")
                if current_monitor_record
                else None
            )

        enriched_assets = []
        for asset in assets:
            if asset.get("hostname") == current_hostname:
                last_active_time = current_monitor_record.get("timestamp") if current_monitor_record else None
                active_application = (
                    current_monitor_record.get("application_name")
                    if current_monitor_record
                    else activity.get("active_process_name")
                )
                enriched_assets.append({
                    **asset,
                    **activity,
                    "currentWebsite": current_activity,
                    "current_website": current_activity,
                    "current_active_path": current_activity,
                    "active_window": activity.get("active_window_title"),
                    "active_application": active_application,
                    "current_application": active_application,
                    "last_active_time": last_active_time,
                })
            else:
                monitor_record = get_latest_active_application_for_host(asset.get("hostname"))
                if monitor_record:
                    enriched_assets.append({
                        **asset,
                        "active_application": monitor_record.get("application_name"),
                        "current_application": monitor_record.get("application_name"),
                        "active_window": monitor_record.get("window_title"),
                        "last_active_time": monitor_record.get("timestamp"),
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
@require_auth()
def get_assets():
    """
    GET /api/assets
    Returns all hardware snapshots from PostgreSQL.
    """
    assets = list_assets()
    return jsonify(enrich_assets_with_current_activity(assets))


@app.route("/api/assets/<path:hostname>/details", methods=["GET"])
@require_auth()
def get_asset_detail(hostname):
    """
    GET /api/assets/<hostname>/details
    Returns a single asset with PostgreSQL-backed sessions, alerts,
    application timeline, hardware changes, device timeline, and chart data.
    """
    detail = get_asset_details(hostname)
    if detail is None:
        return jsonify({"error": "Asset not found"}), 404
    return jsonify(detail)


@app.route("/api/alerts", methods=["GET"])
@require_auth()
def get_alerts():
    """
    GET /api/alerts
    Returns all alert records from PostgreSQL.
    """
    return jsonify(list_alerts())


@app.route("/api/active-applications", methods=["GET"])
@require_auth()
def get_active_applications():
    """
    GET /api/active-applications
    Returns the latest active Windows application seen for each monitored host.
    """
    return jsonify(get_latest_active_applications())


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    payload = request.get_json(silent=True) or {}
    identifier = payload.get("username") or payload.get("email") or ""
    password = payload.get("password") or ""
    token_payload = authenticate_local(identifier, password)
    if not token_payload:
        return jsonify({"error": "Invalid username or password."}), 401
    return jsonify(token_payload)


@app.route("/api/early-access", methods=["POST"])
def early_access_request():
    payload = request.get_json(silent=True) or {}
    data, status_code = submit_early_access(payload, request)
    return jsonify(data), status_code


@app.route("/api/admin-signup", methods=["POST"])
def admin_signup():
    payload = request.get_json(silent=True) or {}
    data, status_code = register_admin(payload, request)
    return jsonify(data), status_code


@app.route("/api/auth/refresh", methods=["POST"])
def auth_refresh():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refreshToken") or ""
    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400
    try:
        refreshed = refresh_access_token(refresh_token)
    except Exception:
        refreshed = None
    if not refreshed:
        return jsonify({"error": "Invalid or expired refresh token"}), 401
    return jsonify(refreshed)


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refreshToken") or ""
    if refresh_token:
        revoke_refresh_token(refresh_token)
    return jsonify({"ok": True})


@app.route("/api/auth/me", methods=["GET"])
@require_auth()
def auth_me():
    return jsonify({"user": serialize_user(g.current_user)})


# ============================================================================
# Session Tracking APIs (Feature 1: Login Tracking)
# ============================================================================

@app.route("/current-user", methods=["GET"])
@require_auth()
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
@require_auth()
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
@require_auth()
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
@require_auth()
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
@require_auth()
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
    print_startup_environment_diagnostics()
    try:
        init_db()
        corrected_app_timestamps = normalize_active_application_timestamps()
        if corrected_app_timestamps:
            print(f"[INFO] Corrected {corrected_app_timestamps} future active application timestamps.")
        ensure_auth_schema()
        bootstrap_admin_user()
        bootstrap_local_telemetry()
    except RuntimeError as exc:
        print(exc)
        sys.exit(1)
    if os.environ.get("WERKZEUG_RUN_MAIN") in {None, "true"}:
        start_active_application_monitor()
        start_login_event_monitor()
    print("=" * 70)
    print("  Asset Sentinel Backend")
    print("  Running on http://localhost:5000")
    print("=" * 70)
    print("  Hardware Monitoring APIs:")
    print("    GET /api/assets")
    print("    GET /api/alerts")
    print("    GET /api/active-applications")
    print("=" * 70)
    print("  Session & Activity Tracking APIs (Feature 1):")
    print("    GET /current-user")
    print("    GET /current-session")
    print("    GET /device-status")
    print("    GET /sessions")
    print("    GET /sessions/count")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=True)
