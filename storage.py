import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import delete, desc, func, select

from database import get_db_session
from models import ActiveApplication, ActiveApplicationHistory, Alert, Asset, HardwareChange, SessionRecord


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _parse_required_datetime(value: Any) -> datetime:
    return _parse_datetime(value) or datetime.now(timezone.utc)


def _parse_uuid(value: Any) -> Optional[UUID]:
    if value in (None, ""):
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def _normalize_ip(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def resolve_device_uid(record: Dict[str, Any]) -> str:
    for key in ("uuid", "bios_serial", "baseboard_serial", "composite_id"):
        value = record.get(key)
        if value not in (None, ""):
            return str(value).strip().lower()

    fingerprint = "|".join(
        str(record.get(key) or "").strip().lower()
        for key in ("hostname", "mac_address", "cpu_name", "baseboard_product")
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _human_age(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    now = datetime.now(value.tzinfo or timezone.utc)
    seconds = max(0, int((now - value).total_seconds()))
    if seconds < 60:
        return f"{seconds} seconds ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hours ago"
    return value.isoformat()


def _status_from_last_seen(value: Optional[datetime]) -> str:
    if not value:
        return "Offline"
    now = datetime.now(value.tzinfo or timezone.utc)
    seconds = (now - value).total_seconds()
    if seconds < 30:
        return "Online"
    if seconds <= 120:
        return "Idle"
    return "Offline"


def _duration(start_value: Any, end_value: Any = None) -> Optional[str]:
    start = _parse_datetime(start_value)
    if not start:
        return None
    end = _parse_datetime(end_value) or datetime.now(start.tzinfo or timezone.utc)
    seconds = max(0, int((end - start).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def serialize_asset(row: Asset) -> Dict[str, Any]:
    live_status = _status_from_last_seen(row.last_seen)
    return {
        "device_uid": row.device_uid,
        "hostname": row.hostname,
        "ip_address": _iso(row.ip_address),
        "mac_address": row.mac_address,
        "bios_serial": row.bios_serial,
        "baseboard_serial": row.baseboard_serial,
        "uuid": _iso(row.uuid),
        "composite_id": row.composite_id,
        "cpu_name": row.cpu_name,
        "ram_total_gb": _iso(row.ram_total_gb),
        "baseboard_manufacturer": row.baseboard_manufacturer,
        "baseboard_product": row.baseboard_product,
        "windows_version": row.windows_version,
        "current_website": row.current_website,
        "active_window_title": row.active_window_title,
        "active_process_path": row.active_process_path,
        "active_process_name": row.active_process_name,
        "cpu_usage": _iso(row.cpu_usage_percent),
        "cpu_usage_percent": _iso(row.cpu_usage_percent),
        "cpu_usage_label": f"{_iso(row.cpu_usage_percent)}%" if row.cpu_usage_percent is not None else None,
        "ram_usage": _iso(row.ram_usage_percent),
        "ram_usage_percent": _iso(row.ram_usage_percent),
        "ram_usage_label": f"{_iso(row.ram_usage_percent)}%" if row.ram_usage_percent is not None else None,
        "status": live_status,
        "device_status": live_status,
        "last_seen": _iso(row.last_seen),
        "last_seen_human": _human_age(row.last_seen),
        "collection_method": row.collection_method,
        "collected_at": _iso(row.collected_at),
        "collection_errors": row.collection_errors or [],
    }


def serialize_alert(row: Alert) -> Dict[str, Any]:
    return {
        "alert_type": row.alert_type,
        "hostname": row.hostname,
        "severity": row.severity,
        "timestamp": _iso(row.timestamp),
        "details": row.details or {},
    }


def serialize_session(row: SessionRecord) -> Dict[str, Any]:
    return {
        "event_type": row.event_type,
        "username": row.username,
        "hostname": row.hostname,
        "ip_address": _iso(row.ip_address),
        "session_id": row.session_id,
        "login_timestamp": _iso(row.login_timestamp),
        "logout_timestamp": _iso(row.logout_timestamp),
        "session_duration": row.session_duration,
        "active": row.active,
        "device_status": row.device_status,
        "last_seen": _iso(row.last_seen),
        "recorded_at": _iso(row.recorded_at),
    }


def serialize_active_application(row: ActiveApplication) -> Dict[str, Any]:
    return {
        "hostname": row.hostname,
        "username": row.username,
        "application_name": row.application_name,
        "executable_name": row.executable_name,
        "window_title": row.window_title,
        "timestamp": _iso(row.timestamp),
    }


def serialize_active_application_history(row: ActiveApplicationHistory) -> Dict[str, Any]:
    return {
        "hostname": row.hostname,
        "username": row.username,
        "application": row.application,
        "application_name": row.application,
        "window_title": row.window_title,
        "process_path": row.process_path,
        "timestamp": _iso(row.timestamp),
    }


def list_assets() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        rows = session.execute(select(Asset).order_by(Asset.hostname.asc())).scalars().all()
        assets = []
        for row in rows:
            asset = serialize_asset(row)
            asset.update(_session_summary(session, row.hostname))
            asset.update(_alert_summary(session, row.hostname))
            asset.update(_activity_summary(session, row.hostname))
            assets.append(asset)
        return assets


def _apply_asset_record(row: Asset, record: Dict[str, Any]) -> Asset:
    row.device_uid = resolve_device_uid(record)
    row.hostname = record.get("hostname") or row.hostname or "Unknown"
    row.ip_address = _normalize_ip(record.get("ip_address"))
    row.mac_address = record.get("mac_address")
    row.bios_serial = record.get("bios_serial")
    row.baseboard_serial = record.get("baseboard_serial")
    row.uuid = _parse_uuid(record.get("uuid"))
    row.composite_id = record.get("composite_id")
    row.cpu_name = record.get("cpu_name")
    row.ram_total_gb = record.get("ram_total_gb")
    row.baseboard_manufacturer = record.get("baseboard_manufacturer")
    row.baseboard_product = record.get("baseboard_product")
    row.windows_version = record.get("windows_version")
    row.current_website = record.get("current_website")
    row.active_window_title = record.get("active_window_title")
    row.active_process_path = record.get("active_process_path")
    row.active_process_name = record.get("active_process_name")
    row.cpu_usage_percent = record.get("cpu_usage_percent")
    row.ram_usage_percent = record.get("ram_usage_percent")
    row.last_seen = _parse_required_datetime(record.get("last_seen") or record.get("collected_at"))
    row.status = _status_from_last_seen(row.last_seen)
    row.collection_method = record.get("collection_method") or "none"
    row.collection_errors = record.get("collection_errors") or []
    row.collected_at = _parse_required_datetime(record.get("collected_at"))
    return row


def upsert_asset(record: Dict[str, Any]) -> None:
    device_uid = resolve_device_uid(record)
    with get_db_session() as session:
        row = session.execute(select(Asset).where(Asset.device_uid == device_uid).limit(1)).scalar_one_or_none()
        if row is None:
            row = Asset(
                device_uid=device_uid,
                hostname=record.get("hostname") or "Unknown",
                collected_at=_parse_required_datetime(record.get("collected_at")),
            )
            session.add(row)
        _apply_asset_record(row, record)


def append_asset(record: Dict[str, Any]) -> None:
    upsert_asset(record)


def _legacy_build_asset(record: Dict[str, Any]) -> Asset:
    return Asset(
        device_uid=resolve_device_uid(record),
        hostname=record.get("hostname") or "Unknown",
        ip_address=_normalize_ip(record.get("ip_address")),
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
        current_website=record.get("current_website"),
        active_window_title=record.get("active_window_title"),
        active_process_path=record.get("active_process_path"),
        active_process_name=record.get("active_process_name"),
        collection_method=record.get("collection_method") or "none",
        collection_errors=record.get("collection_errors") or [],
        collected_at=_parse_required_datetime(record.get("collected_at")),
    )


def list_alerts() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        rows = session.execute(select(Alert).order_by(Alert.timestamp.asc(), Alert.id.asc())).scalars().all()
        return [serialize_alert(row) for row in rows]


def append_alert(alert_type: str, hostname: str, severity: str, details: Dict[str, Any], timestamp: Any = None) -> Dict[str, Any]:
    row = Alert(
        alert_type=alert_type,
        hostname=hostname or "Unknown",
        severity=severity,
        timestamp=_parse_required_datetime(timestamp),
        details=details or {},
    )
    with get_db_session() as session:
        session.add(row)
        session.flush()
        return serialize_alert(row)


def list_sessions() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        rows = session.execute(select(SessionRecord).order_by(SessionRecord.recorded_at.asc(), SessionRecord.id.asc())).scalars().all()
        return [serialize_session(row) for row in rows]


def _session_summary(session, hostname: str) -> Dict[str, Any]:
    rows = session.execute(
        select(SessionRecord)
        .where(SessionRecord.hostname == hostname)
        .order_by(SessionRecord.recorded_at.asc(), SessionRecord.id.asc())
    ).scalars().all()
    if not rows:
        return {"logins_today": 0}

    latest = rows[-1]
    today = datetime.now(timezone.utc).date()
    logins_today = 0
    for row in rows:
        stamp = row.login_timestamp or row.recorded_at
        if row.event_type == "LOGIN" and stamp and stamp.astimezone(timezone.utc).date() == today:
            logins_today += 1

    return {
        "current_user": latest.username,
        "username": latest.username,
        "session_id": latest.session_id,
        "login_timestamp": _iso(latest.login_timestamp or latest.recorded_at),
        "last_login": _iso(latest.login_timestamp or latest.recorded_at),
        "logout_timestamp": _iso(latest.logout_timestamp),
        "last_logout": _iso(latest.logout_timestamp),
        "session_duration": latest.session_duration if latest.session_duration and latest.session_duration != "Active" else _duration(latest.login_timestamp or latest.recorded_at),
        "logins_today": logins_today,
        "active_session": latest.active,
    }


def _alert_summary(session, hostname: str) -> Dict[str, Any]:
    rows = session.execute(
        select(Alert).where(Alert.hostname == hostname).order_by(Alert.timestamp.desc()).limit(20)
    ).scalars().all()
    severity_rank = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
    highest = max((row.severity for row in rows), key=lambda sev: severity_rank.get(sev, 0), default=None)
    alert_status = "critical" if highest == "CRITICAL" else "warning" if highest in {"HIGH", "MEDIUM"} else "nominal"
    threat_score = 92 if alert_status == "critical" else 54 if alert_status == "warning" else 12
    return {
        "alerts": [row.alert_type for row in rows],
        "alert_status": alert_status,
        "alertStatus": alert_status,
        "threat_score": threat_score,
        "hardware_changes": [row.alert_type for row in rows if "CHANGE" in row.alert_type],
    }


def _activity_summary(session, hostname: str) -> Dict[str, Any]:
    latest = session.execute(
        select(ActiveApplication)
        .where(ActiveApplication.hostname == hostname)
        .order_by(ActiveApplication.timestamp.desc(), ActiveApplication.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    history = session.execute(
        select(ActiveApplicationHistory)
        .where(ActiveApplicationHistory.hostname == hostname)
        .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
        .limit(10)
    ).scalars().all()
    if not latest and not history:
        return {"application_history": []}
    latest_payload = serialize_active_application(latest) if latest else {}
    return {
        "active_application": latest_payload.get("application_name"),
        "current_application": latest_payload.get("application_name"),
        "active_window": latest_payload.get("window_title"),
        "current_active_path": latest_payload.get("executable_name"),
        "last_active_time": latest_payload.get("timestamp"),
        "application_history": [serialize_active_application_history(row) for row in history],
    }


def replace_sessions(records: Iterable[Dict[str, Any]]) -> None:
    with get_db_session() as session:
        session.execute(delete(SessionRecord))
        for record in records:
            session.add(_build_session_record(record))


def append_session(record: Dict[str, Any]) -> None:
    with get_db_session() as session:
        session.add(_build_session_record(record))


def touch_active_session(hostname: str, username: Optional[str], session_id: Optional[str]) -> None:
    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        query = (
            select(SessionRecord)
            .where(SessionRecord.hostname == hostname)
            .where(SessionRecord.active.is_(True))
            .order_by(SessionRecord.recorded_at.desc(), SessionRecord.id.desc())
            .limit(1)
        )
        if username:
            query = query.where(SessionRecord.username == username)
        if session_id:
            query = query.where(SessionRecord.session_id == session_id)
        row = session.execute(query).scalar_one_or_none()
        if row:
            row.last_seen = now
            row.device_status = "Online"
            row.session_duration = _duration(row.login_timestamp or row.recorded_at, now) or row.session_duration


def _build_session_record(record: Dict[str, Any]) -> SessionRecord:
    return SessionRecord(
        event_type=record.get("event_type") or "LOGIN",
        username=record.get("username"),
        hostname=record.get("hostname") or "Unknown",
        ip_address=_normalize_ip(record.get("ip_address")),
        session_id=record.get("session_id"),
        login_timestamp=_parse_datetime(record.get("login_timestamp")),
        logout_timestamp=_parse_datetime(record.get("logout_timestamp")),
        session_duration=record.get("session_duration"),
        active=bool(record.get("active", False)),
        device_status=record.get("device_status"),
        last_seen=_parse_datetime(record.get("last_seen")),
        recorded_at=_parse_required_datetime(record.get("recorded_at")),
    )


def list_active_applications_history() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        rows = session.execute(
            select(ActiveApplication).order_by(ActiveApplication.timestamp.asc(), ActiveApplication.id.asc())
        ).scalars().all()
        return [serialize_active_application(row) for row in rows]


def append_active_application(record: Dict[str, Any]) -> None:
    row = ActiveApplication(
        hostname=record.get("hostname") or "Unknown",
        username=record.get("username"),
        application_name=record.get("application_name"),
        executable_name=record.get("executable_name"),
        window_title=record.get("window_title"),
        timestamp=_parse_required_datetime(record.get("timestamp")),
    )
    with get_db_session() as session:
        session.add(row)
        session.add(ActiveApplicationHistory(
            hostname=record.get("hostname") or "Unknown",
            username=record.get("username"),
            application=record.get("application_name"),
            window_title=record.get("window_title"),
            process_path=record.get("process_path") or record.get("active_process_path") or record.get("executable_name"),
            timestamp=_parse_required_datetime(record.get("timestamp")),
        ))


def update_asset_heartbeat(hostname: str, cpu_usage: Any = None, ram_usage: Any = None, activity: Optional[Dict[str, Any]] = None) -> None:
    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        row = session.execute(select(Asset).where(Asset.hostname == hostname).limit(1)).scalar_one_or_none()
        if row is None:
            return
        row.last_seen = now
        row.status = "Online"
        if cpu_usage is not None:
            row.cpu_usage_percent = cpu_usage
        if ram_usage is not None:
            row.ram_usage_percent = ram_usage
        if activity:
            row.active_process_name = activity.get("executable_name") or row.active_process_name
            row.active_window_title = activity.get("window_title") or row.active_window_title
            row.active_process_path = activity.get("process_path") or row.active_process_path
            row.current_website = activity.get("window_title") or row.current_website


def get_latest_active_applications() -> List[Dict[str, Any]]:
    history = list_active_applications_history()
    latest_by_host: Dict[str, Dict[str, Any]] = {}
    for record in history:
        hostname = record.get("hostname")
        if hostname:
            latest_by_host[hostname] = record
    return list(latest_by_host.values())


def get_latest_active_application_for_host(hostname: str) -> Optional[Dict[str, Any]]:
    if not hostname:
        return None
    with get_db_session() as session:
        row = session.execute(
            select(ActiveApplication)
            .where(ActiveApplication.hostname == hostname)
            .order_by(desc(ActiveApplication.timestamp), desc(ActiveApplication.id))
            .limit(1)
        ).scalar_one_or_none()
        return serialize_active_application(row) if row else None


def record_hardware_change(
    hostname: str,
    change_type: str,
    severity: str,
    previous_value: Dict[str, Any],
    current_value: Dict[str, Any],
    difference: Dict[str, Any],
    detected_at: Any = None,
) -> None:
    row = HardwareChange(
        hostname=hostname or "Unknown",
        change_type=change_type,
        severity=severity,
        previous_value=previous_value or {},
        current_value=current_value or {},
        difference=difference or {},
        detected_at=_parse_required_datetime(detected_at),
    )
    with get_db_session() as session:
        session.add(row)
