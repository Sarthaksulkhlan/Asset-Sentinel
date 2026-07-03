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
from typing import Any, Dict, List, Tuple

from sqlalchemy import and_, select

from database import get_db_session, init_db
from models import ActiveApplication, Alert, Asset, SessionRecord
from storage import _parse_datetime, _parse_required_datetime, _parse_uuid, resolve_device_uid


ROOT = Path(__file__).resolve().parent
REPORT_FILE = ROOT / "migration_report.json"

JSON_SOURCES = {
    "assets": ROOT / "assets.json",
    "alerts": ROOT / "alerts.json",
    "sessions": ROOT / "sessions.json",
    "active_applications": ROOT / "active_applications.json",
}


def load_json_array(path: Path) -> Tuple[List[Dict[str, Any]], str | None]:
    if not path.exists():
        return [], "missing"
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return [], "empty"
        data = json.loads(content)
        if not isinstance(data, list):
            return [], "not_array"
        return [item for item in data if isinstance(item, dict)], None
    except Exception as exc:
        return [], f"error: {exc}"


def normalize_ip(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def asset_exists(session, record: Dict[str, Any]) -> bool:
    return session.execute(
        select(Asset.id)
        .where(Asset.device_uid == resolve_device_uid(record))
        .limit(1)
    ).scalar_one_or_none() is not None


def build_asset(record: Dict[str, Any]) -> Asset:
    return Asset(
        device_uid=resolve_device_uid(record),
        hostname=record.get("hostname") or "Unknown",
        ip_address=normalize_ip(record.get("ip_address")),
        mac_address=record.get("mac_address"),
        bios_serial=record.get("bios_serial"),
        baseboard_serial=record.get("baseboard_serial"),
        uuid=_parse_uuid(record.get("uuid")),
        composite_id=record.get("composite_id"),
        cpu_name=record.get("cpu_name"),
        ram_total_gb=record.get("ram_total_gb"),
        baseboard_manufacturer=record.get("baseboard_manufacturer"),
        baseboard_product=record.get("baseboard_product"),
        windows_version=record.get("windows_version"),
        current_website=record.get("current_website") or record.get("currentWebsite"),
        active_window_title=record.get("active_window_title"),
        active_process_path=record.get("active_process_path"),
        active_process_name=record.get("active_process_name"),
        cpu_usage_percent=record.get("cpu_usage_percent"),
        ram_usage_percent=record.get("ram_usage_percent"),
        last_seen=_parse_required_datetime(record.get("last_seen") or record.get("collected_at")),
        status="Online",
        collection_method=record.get("collection_method") or "none",
        collection_errors=record.get("collection_errors") or [],
        collected_at=_parse_required_datetime(record.get("collected_at")),
    )


def alert_exists(session, record: Dict[str, Any]) -> bool:
    timestamp = _parse_required_datetime(record.get("timestamp"))
    return session.execute(
        select(Alert.id)
        .where(Alert.alert_type == (record.get("alert_type") or "UNKNOWN"))
        .where(Alert.hostname == (record.get("hostname") or "Unknown"))
        .where(Alert.severity == (record.get("severity") or "LOW"))
        .where(Alert.timestamp == timestamp)
        .limit(1)
    ).scalar_one_or_none() is not None


def build_alert(record: Dict[str, Any]) -> Alert:
    return Alert(
        alert_type=record.get("alert_type") or "UNKNOWN",
        hostname=record.get("hostname") or "Unknown",
        severity=record.get("severity") or "LOW",
        timestamp=_parse_required_datetime(record.get("timestamp")),
        details=record.get("details") or {},
    )


def session_exists(session, record: Dict[str, Any]) -> bool:
    recorded_at = _parse_required_datetime(record.get("recorded_at"))
    conditions = [
        SessionRecord.event_type == (record.get("event_type") or "LOGIN"),
        SessionRecord.hostname == (record.get("hostname") or "Unknown"),
        SessionRecord.recorded_at == recorded_at,
    ]

    username = record.get("username")
    session_id = record.get("session_id")
    conditions.append(SessionRecord.username.is_(None) if username is None else SessionRecord.username == username)
    conditions.append(SessionRecord.session_id.is_(None) if session_id is None else SessionRecord.session_id == session_id)

    return session.execute(select(SessionRecord.id).where(and_(*conditions)).limit(1)).scalar_one_or_none() is not None


def build_session(record: Dict[str, Any]) -> SessionRecord:
    return SessionRecord(
        event_type=record.get("event_type") or "LOGIN",
        username=record.get("username"),
        hostname=record.get("hostname") or "Unknown",
        ip_address=normalize_ip(record.get("ip_address")),
        session_id=record.get("session_id"),
        login_timestamp=_parse_datetime(record.get("login_timestamp")),
        logout_timestamp=_parse_datetime(record.get("logout_timestamp")),
        session_duration=record.get("session_duration"),
        active=bool(record.get("active", record.get("device_status") == "Online")),
        device_status=record.get("device_status"),
        last_seen=_parse_datetime(record.get("last_seen")),
        recorded_at=_parse_required_datetime(record.get("recorded_at")),
    )


def active_application_exists(session, record: Dict[str, Any]) -> bool:
    timestamp = _parse_required_datetime(record.get("timestamp"))
    fields = {
        "hostname": record.get("hostname") or "Unknown",
        "username": record.get("username"),
        "executable_name": record.get("executable_name"),
        "window_title": record.get("window_title"),
    }
    conditions = [ActiveApplication.timestamp == timestamp]
    for field, value in fields.items():
        column = getattr(ActiveApplication, field)
        conditions.append(column.is_(None) if value is None else column == value)
    return session.execute(select(ActiveApplication.id).where(and_(*conditions)).limit(1)).scalar_one_or_none() is not None


def build_active_application(record: Dict[str, Any]) -> ActiveApplication:
    return ActiveApplication(
        hostname=record.get("hostname") or "Unknown",
        username=record.get("username"),
        application_name=record.get("application_name"),
        executable_name=record.get("executable_name"),
        window_title=record.get("window_title"),
        timestamp=_parse_required_datetime(record.get("timestamp")),
    )


MIGRATORS = {
    "assets": (asset_exists, build_asset),
    "alerts": (alert_exists, build_alert),
    "sessions": (session_exists, build_session),
    "active_applications": (active_application_exists, build_active_application),
}


def migrate_dataset(name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    exists_fn, build_fn = MIGRATORS[name]
    result = {
        "source": str(JSON_SOURCES[name].name),
        "read": len(records),
        "inserted": 0,
        "skipped_duplicates": 0,
        "failed": 0,
        "errors": [],
    }

    with get_db_session() as session:
        for index, record in enumerate(records):
            try:
                if exists_fn(session, record):
                    result["skipped_duplicates"] += 1
                    continue
                session.add(build_fn(record))
                session.flush()
                result["inserted"] += 1
            except Exception as exc:
                session.rollback()
                result["failed"] += 1
                result["errors"].append({"index": index, "error": str(exc)})

    return result


def main() -> int:
    init_db()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database": "asset_sentinel",
        "status": "completed",
        "datasets": {},
    }

    for name, path in JSON_SOURCES.items():
        records, issue = load_json_array(path)
        if issue:
            report["datasets"][name] = {
                "source": path.name,
                "read": 0,
                "inserted": 0,
                "skipped_duplicates": 0,
                "failed": 0,
                "status": issue,
                "errors": [],
            }
            continue

        result = migrate_dataset(name, records)
        result["status"] = "ok" if result["failed"] == 0 else "partial"
        report["datasets"][name] = result

    if any(item["failed"] for item in report["datasets"].values()):
        report["status"] = "completed_with_errors"

    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    return 1 if report["status"] == "completed_with_errors" else 0


if __name__ == "__main__":
    raise SystemExit(main())

