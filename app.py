import os
import sys
import logging
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from config import print_startup_environment_diagnostics
from active_application_monitor import get_latest_active_applications

# Import session tracking modules
from activity_api import (
    get_current_user,
    get_current_session,
    get_device_status_endpoint,
    get_sessions_history,
    get_sessions_count,
)
from database import database_host_for_display, init_db
from service_logging import configure_logging, has_asset_sentinel_file_logging
from storage import get_asset_details, list_alerts, list_assets, normalize_active_application_timestamps
from startup_health import device_health_response, run_startup_checks, startup_health_response
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
    if (
        request.path.startswith("/api/assets")
        or request.path in {"/api/active-applications", "/api/sessions", "/api/sessions/count"}
        or request.path in {"/sessions", "/sessions/count", "/device-status", "/current-session", "/current-user"}
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

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
    return jsonify(list_assets())


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


@app.route("/api/database/host", methods=["GET"])
@require_auth()
def get_database_host():
    return jsonify({"host": database_host_for_display(), "source": "ASSET_SENTINEL_DATABASE_URL"})


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


@app.route("/api/debug/startup-health", methods=["GET"])
def debug_startup_health():
    return jsonify(startup_health_response())


@app.route("/api/debug/device-health/<path:hostname>", methods=["GET"])
def debug_device_health(hostname):
    health = device_health_response(hostname)
    if health is None:
        return jsonify({"error": "Device not found", "identifier": hostname}), 404
    return jsonify(health)


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


def initialize_backend_runtime(start_agent: bool = True, exit_on_error: bool = True) -> bool:
    if not has_asset_sentinel_file_logging():
        configure_logging("app", console=True)
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
        logging.getLogger("asset_sentinel.backend").exception("Backend runtime initialization failed: %s", exc)
        if exit_on_error:
            sys.exit(1)
        return False
    if os.environ.get("WERKZEUG_RUN_MAIN") in {None, "true"}:
        start_local_agent = (
            start_agent
            and os.environ.get("ASSET_SENTINEL_DISABLE_LOCAL_AGENT", "").lower() not in {"1", "true", "yes"}
        )
        run_startup_checks(start_agent=start_local_agent)
    else:
        print("[INFO] Flask reloader parent process skipped local telemetry startup.")
    return True


def print_backend_banner(host: str = "0.0.0.0", port: int = 5000) -> None:
    print("=" * 70)
    print("  Asset Sentinel Backend")
    print(f"  Running on http://{host}:{port}")
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


def run_backend(host: str = "0.0.0.0", port: int = 5000, debug: bool = True, start_agent: bool = True) -> None:
    initialize_backend_runtime(start_agent=start_agent, exit_on_error=True)
    print_backend_banner(host, port)
    app.run(host=host, port=port, debug=debug, use_reloader=debug)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_backend()
