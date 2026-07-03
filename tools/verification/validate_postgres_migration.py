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
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import text

from active_application_monitor import collect_active_application_record
from app import app
from collect_hardware import collect_hardware
from auth import create_access_token
from database import SessionLocal, engine
from login_tracker import load_sessions
from models import ActiveApplication, Alert, Asset, SessionRecord, User
from session_manager import get_current_session_info


ROOT = Path(__file__).resolve().parent
REPORT_FILE = ROOT / "validation_report.json"


def ok(details: Any = None) -> Dict[str, Any]:
    return {"status": "ok", "details": details}


def fail(exc: Exception) -> Dict[str, Any]:
    return {"status": "failed", "error": str(exc)}


def check_database_connection() -> Dict[str, Any]:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("select 1")).scalar()
        return ok({"select_1": result})
    except Exception as exc:
        return fail(exc)


def check_table_counts() -> Dict[str, Any]:
    try:
        counts = {}
        with engine.connect() as conn:
            for table in ["assets", "alerts", "sessions", "active_applications", "hardware_changes", "users"]:
                counts[table] = conn.execute(text(f"select count(*) from {table}")).scalar()
        return ok(counts)
    except Exception as exc:
        return fail(exc)


def check_crud_rollback() -> Dict[str, Any]:
    session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        asset = Asset(
            device_uid="validation-host",
            hostname="VALIDATION-HOST",
            collection_method="none",
            collected_at=now,
            last_seen=now,
            status="Online",
        )
        alert = Alert(
            alert_type="VALIDATION",
            hostname="VALIDATION-HOST",
            severity="LOW",
            timestamp=now,
            details={"validation": True},
        )
        session_record = SessionRecord(
            event_type="LOGIN",
            username="validation",
            hostname="VALIDATION-HOST",
            recorded_at=now,
            active=True,
            device_status="Online",
        )
        activity = ActiveApplication(
            hostname="VALIDATION-HOST",
            username="validation",
            application_name="validation",
            executable_name="validation.exe",
            window_title="validation",
            timestamp=now,
        )

        session.add_all([asset, alert, session_record, activity])
        session.flush()

        found = session.execute(
            text("select count(*) from assets where hostname = 'VALIDATION-HOST'")
        ).scalar()
        session.rollback()
        return ok({"inserted_inside_transaction": found, "rolled_back": True})
    except Exception as exc:
        session.rollback()
        return fail(exc)
    finally:
        session.close()


def check_api_contracts() -> Dict[str, Any]:
    endpoints = [
        "/api/assets",
        "/api/alerts",
        "/api/sessions",
        "/api/active-applications",
        "/api/sessions/count",
        "/current-user",
        "/current-session",
        "/device-status",
    ]
    results = {}
    try:
        with app.test_client() as client:
            with SessionLocal() as session:
                user = session.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
                if not user:
                    raise RuntimeError("No active user exists for authenticated API validation.")
                session.expunge(user)
            token = create_access_token(user)
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            results["auth_context"] = {"status_code": 200, "json_type": "direct_token", "keys": ["Authorization"]}
            for endpoint in endpoints:
                response = client.get(endpoint, headers=headers)
                payload = response.get_json(silent=True)
                results[endpoint] = {
                    "status_code": response.status_code,
                    "json_type": type(payload).__name__,
                    "top_level_count": len(payload) if isinstance(payload, list) else None,
                    "keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
                }
        failed = [endpoint for endpoint, result in results.items() if result["status_code"] >= 400]
        return {"status": "failed" if failed else "ok", "details": results}
    except Exception as exc:
        return fail(exc)


def check_hardware_collection() -> Dict[str, Any]:
    try:
        data = collect_hardware()
        required = ["hostname", "ip_address", "bios_serial", "ram_total_gb", "collected_at", "collection_method"]
        return ok({"keys_present": {key: key in data for key in required}, "collection_method": data.get("collection_method")})
    except Exception as exc:
        return fail(exc)


def check_login_tracking_read() -> Dict[str, Any]:
    try:
        session_info = get_current_session_info()
        sessions = load_sessions()
        return ok({
            "current_session_keys": sorted(session_info.keys()),
            "stored_sessions": len(sessions),
        })
    except Exception as exc:
        return fail(exc)


def check_active_application_collection() -> Dict[str, Any]:
    try:
        record = collect_active_application_record()
        return ok({"record_available": record is not None, "keys": sorted(record.keys()) if record else []})
    except Exception as exc:
        return fail(exc)


def check_json_runtime_dependencies() -> Dict[str, Any]:
    patterns = ["read_text", "write_text", "assets.json", "alerts.json", "sessions.json", "active_applications.json"]
    findings = {}
    for path in ROOT.glob("*.py"):
        if path.name in {"migrate_json_to_postgres.py", "validate_postgres_migration.py"}:
            continue
        content = path.read_text(encoding="utf-8")
        matches = [pattern for pattern in patterns if pattern in content]
        if matches:
            findings[path.name] = matches
    return ok({"runtime_json_references": findings})


def main() -> int:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "checks": {
            "database_connection": check_database_connection(),
            "table_counts": check_table_counts(),
            "crud_rollback": check_crud_rollback(),
            "api_contracts": check_api_contracts(),
            "hardware_collection": check_hardware_collection(),
            "login_tracking_read": check_login_tracking_read(),
            "active_application_collection": check_active_application_collection(),
            "json_runtime_dependencies": check_json_runtime_dependencies(),
        },
    }

    failed = [name for name, result in report["checks"].items() if result.get("status") != "ok"]
    if failed:
        report["status"] = "completed_with_failures"
        report["failed_checks"] = failed

    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

