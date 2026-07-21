import os
import sys
import logging
import traceback

if __package__ in {None, ""}:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend._bootstrap import bootstrap_paths

bootstrap_paths()

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from config import print_startup_environment_diagnostics

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
from storage import (
    get_asset_details,
    get_latest_active_applications,
    list_active_application_history_for_asset,
    list_alerts,
    list_assets,
    normalize_active_application_timestamps,
)
from startup_health import device_health_response, run_startup_checks, startup_health_response
from registration import register_admin, submit_early_access
from backend.api.agent import agent_api
from auth import (
    ROLE_SUPER_ADMIN,
    authenticate_local,
    bootstrap_admin_user,
    ensure_auth_schema,
    refresh_access_token,
    require_auth,
    revoke_refresh_token,
    request_password_reset_otp,
    reset_password_with_otp,
    serialize_user,
    normalize_role,
    verify_password_reset_otp,
)
from support import create_support_ticket, list_support_tickets, send_support_message, update_support_ticket
from super_admin import all_support_tickets, company_detail, list_companies, super_admin_overview, update_company_status

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
cors_origins = [
    origin.strip()
    for origin in os.environ.get("ASSET_SENTINEL_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
CORS(
    app,
    origins=cors_origins or ["*"],
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
)  # Allow configured React frontend origins and auth headers
app.register_blueprint(agent_api)


@app.after_request
def add_live_api_cache_headers(response):
    if (
        request.path.startswith("/api/assets")
        or request.path.startswith("/api/active-application-history")
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

def _request_company_scope():
    user = getattr(g, "current_user", None)
    if not user or normalize_role(user.role) == ROLE_SUPER_ADMIN:
        return None
    return getattr(user, "company_id", None)

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
    return jsonify(list_assets(_request_company_scope()))


@app.route("/api/assets/<path:hostname>/details", methods=["GET"])
@require_auth()
def get_asset_detail(hostname):
    """
    GET /api/assets/<hostname>/details
    Returns a single asset with PostgreSQL-backed sessions, alerts,
    application timeline, hardware changes, device timeline, and chart data.
    """
    detail = get_asset_details(hostname, _request_company_scope())
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
    return jsonify(list_alerts(_request_company_scope()))


@app.route("/api/active-applications", methods=["GET"])
@require_auth()
def get_active_applications():
    """
    GET /api/active-applications
    Returns the latest active Windows application seen for each monitored host.
    """
    return jsonify(get_latest_active_applications(_request_company_scope()))


@app.route("/api/active-application-history/<path:hostname>", methods=["GET"])
@require_auth()
def get_active_application_history(hostname):
    """
    GET /api/active-application-history/<hostname-or-device-id>
    Returns recent active application timeline entries without recomputing
    the full asset detail analytics payload.
    """
    try:
        limit = int(request.args.get("limit") or "100")
    except ValueError:
        limit = 100
    history = list_active_application_history_for_asset(hostname, _request_company_scope(), limit)
    if history is None:
        return jsonify({"error": "Asset not found"}), 404
    return jsonify({"application_timeline": history})


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


@app.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    payload = request.get_json(silent=True) or {}
    return jsonify(request_password_reset_otp(payload.get("identifier") or payload.get("email") or ""))


@app.route("/api/auth/verify-reset-code", methods=["POST"])
def auth_verify_reset_code():
    payload = request.get_json(silent=True) or {}
    data, status_code = verify_password_reset_otp(
        payload.get("identifier") or payload.get("email") or "",
        payload.get("otp") or "",
    )
    return jsonify(data), status_code


@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    payload = request.get_json(silent=True) or {}
    data, status_code = reset_password_with_otp(
        payload.get("identifier") or payload.get("email") or "",
        payload.get("otp") or "",
        payload.get("new_password") or "",
    )
    return jsonify(data), status_code


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


@app.route("/api/support/tickets", methods=["GET"])
@require_auth()
def support_tickets_list():
    data, status_code = list_support_tickets()
    return jsonify(data), status_code


@app.route("/api/support/tickets", methods=["POST"])
@require_auth()
def support_tickets_create():
    payload = request.get_json(silent=True) or {}
    data, status_code = create_support_ticket(payload)
    return jsonify(data), status_code


@app.route("/api/support/tickets/<int:ticket_id>", methods=["PATCH"])
@require_auth({ROLE_SUPER_ADMIN})
def support_tickets_update(ticket_id: int):
    payload = request.get_json(silent=True) or {}
    data, status_code = update_support_ticket(ticket_id, payload)
    return jsonify(data), status_code


@app.route("/api/support/email", methods=["POST"])
@require_auth()
def support_email():
    payload = request.get_json(silent=True) or {}
    data, status_code = send_support_message(payload)
    return jsonify(data), status_code


@app.route("/api/super-admin/overview", methods=["GET"])
@require_auth({ROLE_SUPER_ADMIN})
def super_admin_overview_endpoint():
    return jsonify(super_admin_overview())


@app.route("/api/super-admin/companies", methods=["GET"])
@require_auth({ROLE_SUPER_ADMIN})
def super_admin_companies_endpoint():
    return jsonify(list_companies())


@app.route("/api/super-admin/company/<int:company_id>", methods=["GET"])
@require_auth({ROLE_SUPER_ADMIN})
def super_admin_company_detail_endpoint(company_id: int):
    data, status_code = company_detail(company_id)
    return jsonify(data), status_code


@app.route("/api/super-admin/company/<int:company_id>", methods=["PATCH"])
@require_auth({ROLE_SUPER_ADMIN})
def super_admin_company_update_endpoint(company_id: int):
    payload = request.get_json(silent=True) or {}
    data, status_code = update_company_status(company_id, payload.get("status") or "")
    return jsonify(data), status_code


@app.route("/api/super-admin/tickets", methods=["GET"])
@require_auth({ROLE_SUPER_ADMIN})
def super_admin_tickets_endpoint():
    return jsonify(all_support_tickets())


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
    startup_logger = logging.getLogger("asset_sentinel.backend")
    current_step = "Environment"
    try:
        print(f"[STARTUP] {current_step}: checking configuration", flush=True)
        print_startup_environment_diagnostics()

        current_step = "Database"
        print(f"[STARTUP] {current_step}: creating/verifying tables", flush=True)
        init_db()
        print(f"[STARTUP] {current_step}: ready", flush=True)

        current_step = "Application Data"
        print(f"[STARTUP] {current_step}: normalizing timestamps", flush=True)
        corrected_app_timestamps = normalize_active_application_timestamps()
        if corrected_app_timestamps:
            print(f"[INFO] Corrected {corrected_app_timestamps} future active application timestamps.", flush=True)

        current_step = "Auth"
        print(f"[STARTUP] {current_step}: ensuring schema", flush=True)
        ensure_auth_schema()
        print(f"[STARTUP] {current_step}: ready", flush=True)

        current_step = "Admin"
        print(f"[STARTUP] {current_step}: bootstrapping super admin", flush=True)
        bootstrap_admin_user()
        print(f"[STARTUP] {current_step}: ready", flush=True)

        current_step = "SMTP"
        smtp_configured = bool(os.environ.get("SMTP_USERNAME") and os.environ.get("SMTP_PASSWORD"))
        print(
            f"[STARTUP] {current_step}: {'configured' if smtp_configured else 'not configured (optional)'}",
            flush=True,
        )

        current_step = "Routes"
        print(f"[STARTUP] {current_step}: {len(list(app.url_map.iter_rules()))} registered", flush=True)
    except Exception as exc:
        print(f"[STARTUP] FAILED at step: {current_step}", file=sys.stderr, flush=True)
        print(f"[STARTUP] {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        startup_logger.exception("Backend runtime initialization failed at step %s", current_step)
        if exit_on_error:
            raise
        return False
    if os.environ.get("WERKZEUG_RUN_MAIN") in {None, "true"}:
        start_local_agent = (
            start_agent
            and os.environ.get("ASSET_SENTINEL_DISABLE_LOCAL_AGENT", "").lower() not in {"1", "true", "yes"}
        )
        if start_local_agent:
            print("[STARTUP] Local Agent: starting Windows telemetry checks", flush=True)
            run_startup_checks(start_agent=True)
        else:
            print("[STARTUP] Local Agent: disabled; local hardware and Windows checks skipped", flush=True)
    else:
        print("[INFO] Flask reloader parent process skipped local telemetry startup.", flush=True)
    print("[STARTUP] App Ready", flush=True)
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
