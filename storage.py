import hashlib
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import delete, desc, func, or_, select, text

from database import get_db_session
from config import Config
from models import ActiveApplication, ActiveApplicationHistory, Alert, Asset, HardwareChange, SessionRecord


logger = logging.getLogger("asset_sentinel.storage")

REAL_LOGIN_SOURCES = {"windows_interactive_logon"}


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.astimezone(timezone.utc)
        return value.replace(tzinfo=_local_tzinfo()).astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo:
                return parsed.astimezone(timezone.utc)
            return parsed.replace(tzinfo=_local_tzinfo()).astimezone(timezone.utc)
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


def _clean_identity_value(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    lowered = text_value.lower()
    if lowered in {"none", "unknown", "unknown host", "to be filled by o.e.m.", "default string", "system serial number"}:
        return None
    return lowered


def identity_candidates(record: Dict[str, Any]) -> List[tuple[str, str]]:
    candidates: List[tuple[str, str]] = []
    for key in ("uuid", "bios_serial", "baseboard_serial", "mac_address", "composite_id", "device_uid"):
        value = _clean_identity_value(record.get(key))
        if value:
            candidates.append((key, value))
    return candidates


def _asset_identity_candidates(row: Asset) -> List[tuple[str, str]]:
    return identity_candidates({
        "uuid": row.uuid,
        "bios_serial": row.bios_serial,
        "baseboard_serial": row.baseboard_serial,
        "mac_address": row.mac_address,
        "composite_id": row.composite_id,
        "device_uid": row.device_uid,
    })


def _human_age(value: Optional[datetime]) -> Optional[str]:
    if not value:
        return None
    now = datetime.now(value.tzinfo or timezone.utc)
    raw_seconds = int((now - value).total_seconds())
    if raw_seconds < -Config.HEARTBEAT_FUTURE_SKEW_SECONDS:
        return f"clock skew: {-raw_seconds} seconds ahead"
    seconds = max(0, raw_seconds)
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
    if seconds < -Config.HEARTBEAT_FUTURE_SKEW_SECONDS:
        return "Offline"
    if seconds <= max(1, Config.HEARTBEAT_TIMEOUT_SECONDS):
        return "Online"
    return "Offline"


def _human_duration(seconds_value: Any) -> Optional[str]:
    if seconds_value in (None, ""):
        return None
    try:
        seconds = int(float(seconds_value))
    except (TypeError, ValueError):
        return None
    days, remainder = divmod(max(0, seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _duration(start_value: Any, end_value: Any = None) -> Optional[str]:
    start = _parse_datetime(start_value)
    if not start:
        return None
    end = _parse_datetime(end_value) or datetime.now(start.tzinfo or timezone.utc)
    seconds = max(0, int((end - start).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def _local_tzinfo():
    return Config.DISPLAY_TZINFO


def _local_date(value: datetime):
    return value.astimezone(_local_tzinfo()).date()


def serialize_asset(row: Asset) -> Dict[str, Any]:
    live_status = _status_from_last_seen(row.last_seen)
    ram_total = float(row.ram_total_gb) if row.ram_total_gb is not None else None
    ram_usage = float(row.ram_usage_percent) if row.ram_usage_percent is not None else None
    memory_used = round(ram_total * (ram_usage / 100), 2) if ram_total is not None and ram_usage is not None else None
    memory_available = round(ram_total - memory_used, 2) if ram_total is not None and memory_used is not None else None
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
        "memory_used_gb": memory_used,
        "memory_available_gb": memory_available,
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
        "login_source": row.login_source,
        "windows_event_id": row.windows_event_id,
        "windows_event_record_id": row.windows_event_record_id,
        "recorded_at": _iso(row.recorded_at),
    }


def serialize_active_application(row: ActiveApplication) -> Dict[str, Any]:
    return {
        "hostname": row.hostname,
        "username": row.username,
        "application_name": row.application_name,
        "executable_name": row.executable_name,
        "window_title": row.window_title,
        "process_path": row.executable_name,
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
        merge_duplicate_assets(session)
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
    if (datetime.now(row.last_seen.tzinfo or timezone.utc) - row.last_seen).total_seconds() < -Config.HEARTBEAT_FUTURE_SKEW_SECONDS:
        row.last_seen = datetime.now(timezone.utc)
    row.status = "Offline"
    row.collection_method = record.get("collection_method") or "none"
    row.collection_errors = record.get("collection_errors") or []
    row.collected_at = _parse_required_datetime(record.get("collected_at"))
    return row


def upsert_asset(record: Dict[str, Any]) -> None:
    device_uid = resolve_device_uid(record)
    with get_db_session() as session:
        row = _find_asset_row(session, record, device_uid)
        if row is None:
            logger.info("Creating PostgreSQL asset row for hostname=%s device_uid=%s", record.get("hostname"), device_uid)
            row = Asset(
                device_uid=device_uid,
                hostname=record.get("hostname") or "Unknown",
                collected_at=_parse_required_datetime(record.get("collected_at")),
            )
            session.add(row)
        else:
            logger.debug("Updating PostgreSQL asset row for hostname=%s device_uid=%s", record.get("hostname"), device_uid)
        _apply_asset_record(row, record)
        merge_duplicate_assets(session)


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
    with get_db_session() as session:
        event_record_id = (details or {}).get("windows_event_record_id")
        if event_record_id:
            existing = session.execute(
                select(Alert)
                .where(Alert.alert_type == alert_type)
                .where(Alert.hostname == (hostname or "Unknown"))
                .where(Alert.details["windows_event_record_id"].as_string() == str(event_record_id))
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                return serialize_alert(existing)
        row = Alert(
            alert_type=alert_type,
            hostname=hostname or "Unknown",
            severity=severity,
            timestamp=_parse_required_datetime(timestamp),
            details=details or {},
        )
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

    login_rows = [row for row in rows if _is_countable_login(row)]
    latest = rows[-1]
    latest_login = login_rows[-1] if login_rows else latest
    active_login = next((row for row in reversed(login_rows) if row.active), latest_login)
    today = datetime.now(_local_tzinfo()).date()
    week_start = today - timedelta(days=today.weekday())
    logins_today = 0
    logins_this_week = 0
    last_successful_login = None
    last_failed_login = None
    last_logout = None
    for row in rows:
        stamp = row.login_timestamp or row.recorded_at
        stamp_date = _local_date(stamp) if stamp else None
        if _is_countable_login(row):
            if stamp_date == today:
                logins_today += 1
            if stamp_date and stamp_date >= week_start:
                logins_this_week += 1
            last_successful_login = stamp
        if row.event_type == "LOGOUT":
            last_logout = row.logout_timestamp or row.recorded_at
        details = getattr(row, "details", None) or {}
        if isinstance(details, dict) and details.get("failed_login_timestamp"):
            last_failed_login = _parse_datetime(details.get("failed_login_timestamp"))

    return {
        "current_user": active_login.username or latest_login.username,
        "username": active_login.username or latest_login.username,
        "session_id": active_login.session_id or latest_login.session_id,
        "login_timestamp": _iso(active_login.login_timestamp or active_login.recorded_at),
        "last_login": _iso(active_login.login_timestamp or active_login.recorded_at),
        "current_login_time": _iso(active_login.login_timestamp or active_login.recorded_at),
        "logout_timestamp": _iso(last_logout or latest.logout_timestamp),
        "last_logout": _iso(last_logout or latest.logout_timestamp),
        "session_duration": active_login.session_duration if active_login.session_duration and active_login.session_duration != "Active" else _duration(active_login.login_timestamp or active_login.recorded_at),
        "total_logins": len(login_rows),
        "logins_today": logins_today,
        "logins_this_week": logins_this_week,
        "last_successful_login": _iso(last_successful_login),
        "last_failed_login": _iso(last_failed_login),
        "active_session": active_login.active,
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


def _is_countable_login(row: SessionRecord) -> bool:
    return row.event_type == "LOGIN" and (row.login_source in REAL_LOGIN_SOURCES)


def _activity_summary(session, hostname: str) -> Dict[str, Any]:
    history = session.execute(
        select(ActiveApplicationHistory)
        .where(ActiveApplicationHistory.hostname == hostname)
        .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
        .limit(10)
    ).scalars().all()
    latest = history[0] if history else None
    if not latest:
        return {"application_history": []}
    latest_payload = serialize_active_application_history(latest)
    return {
        "active_application": latest_payload.get("application_name"),
        "current_application": latest_payload.get("application_name"),
        "active_window": latest_payload.get("window_title"),
        "current_active_path": latest_payload.get("process_path"),
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
        event_record_id = record.get("windows_event_record_id")
        if event_record_id:
            existing = session.execute(
                select(SessionRecord.id)
                .where(SessionRecord.hostname == (record.get("hostname") or "Unknown"))
                .where(SessionRecord.windows_event_record_id == str(event_record_id))
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                return
        if record.get("event_type") == "LOGIN" and record.get("login_source") not in REAL_LOGIN_SOURCES:
            logger.info(
                "Skipping non-login session event: host=%s source=%s event=%s",
                record.get("hostname"),
                record.get("login_source"),
                record.get("windows_event_id"),
            )
            return
        session.add(_build_session_record(record))


def has_session_event_signature(hostname: str, windows_event_record_id: Optional[str]) -> bool:
    if not hostname or not windows_event_record_id:
        return False
    with get_db_session() as session:
        row = session.execute(
            select(SessionRecord.id)
            .where(SessionRecord.hostname == hostname)
            .where(SessionRecord.windows_event_record_id == str(windows_event_record_id))
            .limit(1)
        ).scalar_one_or_none()
        return row is not None


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
        login_source=record.get("login_source"),
        windows_event_id=str(record.get("windows_event_id")) if record.get("windows_event_id") else None,
        windows_event_record_id=str(record.get("windows_event_record_id")) if record.get("windows_event_record_id") else None,
        recorded_at=_parse_required_datetime(record.get("recorded_at")),
    )


def list_active_applications_history() -> List[Dict[str, Any]]:
    with get_db_session() as session:
        rows = session.execute(
            select(ActiveApplicationHistory)
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .limit(500)
        ).scalars().all()
        return [serialize_active_application_history(row) for row in rows]


def append_active_application(record: Dict[str, Any]) -> None:
    event_timestamp = _parse_datetime(record.get("timestamp")) or datetime.now(timezone.utc)
    hostname = record.get("hostname") or "Unknown"
    username = record.get("username")
    application_name = record.get("application_name")
    executable_name = record.get("executable_name")
    window_title = record.get("window_title")
    with get_db_session() as session:
        latest = session.execute(
            select(ActiveApplicationHistory)
            .where(ActiveApplicationHistory.hostname == hostname)
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest and (
            latest.username == username
            and latest.application == application_name
            and latest.window_title == window_title
            and latest.process_path == (record.get("process_path") or record.get("active_process_path") or executable_name)
        ):
            return
        row = ActiveApplication(
            hostname=hostname,
            username=username,
            application_name=application_name,
            executable_name=executable_name,
            window_title=window_title,
            timestamp=event_timestamp,
        )
        session.add(row)
        session.add(ActiveApplicationHistory(
            hostname=hostname,
            username=username,
            application=application_name,
            window_title=window_title,
            process_path=record.get("process_path") or record.get("active_process_path") or executable_name,
            timestamp=event_timestamp,
        ))
        session.flush()
        old_rows = session.execute(
            select(ActiveApplicationHistory.id)
            .where(ActiveApplicationHistory.hostname == (record.get("hostname") or "Unknown"))
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .offset(100)
        ).scalars().all()
        if old_rows:
            session.execute(delete(ActiveApplicationHistory).where(ActiveApplicationHistory.id.in_(old_rows)))


def normalize_active_application_timestamps() -> int:
    local_offset = datetime.now().astimezone().utcoffset()
    if not local_offset:
        return 0

    offset_seconds = int(local_offset.total_seconds())
    if offset_seconds == 0:
        return 0

    statement_template = (
        "UPDATE {table_name} "
        "SET timestamp = timestamp - (:offset_seconds * interval '1 second') "
        "WHERE timestamp > now() + interval '10 seconds'"
    )

    corrected = 0
    with get_db_session() as session:
        for table_name in ("active_applications", "active_application_history"):
            result = session.execute(
                text(statement_template.format(table_name=table_name)),
                {"offset_seconds": offset_seconds},
            )
            corrected += max(result.rowcount or 0, 0)
    return corrected


def update_asset_heartbeat(hostname: str, cpu_usage: Any = None, ram_usage: Any = None, activity: Optional[Dict[str, Any]] = None) -> None:
    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        lookup_record = {"hostname": hostname, **(activity or {})}
        row = _find_asset_row(session, lookup_record, lookup_record.get("device_uid") or "")
        if row is None and hostname:
            row = session.execute(
                select(Asset)
                .where(Asset.hostname == hostname)
                .order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.desc())
                .limit(1)
            ).scalar_one_or_none()
        if row is None:
            logger.warning(
                "Heartbeat skipped because hostname=%s is not present in PostgreSQL assets. "
                "Startup telemetry bootstrap should create it first.",
                hostname,
            )
            return
        row.last_seen = now
        row.status = "Offline"
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
        if hostname and hostname not in latest_by_host:
            latest_by_host[hostname] = record
    return list(latest_by_host.values())


def get_latest_active_application_for_host(hostname: str) -> Optional[Dict[str, Any]]:
    if not hostname:
        return None
    with get_db_session() as session:
        row = session.execute(
            select(ActiveApplicationHistory)
            .where(ActiveApplicationHistory.hostname == hostname)
            .order_by(desc(ActiveApplicationHistory.timestamp), desc(ActiveApplicationHistory.id))
            .limit(1)
        ).scalar_one_or_none()
        return serialize_active_application_history(row) if row else None


def get_asset_status(hostname: str) -> Optional[Dict[str, Any]]:
    with get_db_session() as session:
        row = _find_asset_by_public_identifier(session, hostname)
        if row is None:
            return None
        asset = serialize_asset(row)
        return {
            "hostname": row.hostname,
            "device_uid": row.device_uid,
            "device_status": asset["status"],
            "status": asset["status"],
            "last_seen": asset["last_seen"],
            "last_seen_human": asset["last_seen_human"],
            "heartbeat_timeout_seconds": Config.HEARTBEAT_TIMEOUT_SECONDS,
        }


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


def _severity_label(value: Optional[str]) -> Optional[str]:
    return value.upper() if value else None


def _event_severity(event_type: str, severity: Optional[str] = None) -> Optional[str]:
    if severity:
        return _severity_label(severity)
    if event_type in {"Device Offline", "Motherboard Change"}:
        return "HIGH"
    if event_type in {"RAM Change", "Alert", "Application Closed"}:
        return "MEDIUM"
    return "LOW"


def _timeline_event(timestamp: Any, event_type: str, description: str, severity: Optional[str] = None) -> Dict[str, Any]:
    return {
        "timestamp": _iso(timestamp),
        "type": event_type,
        "event_type": event_type,
        "description": description,
        "detail": description,
        "severity": _event_severity(event_type, severity),
    }


def get_asset_details(hostname: str) -> Optional[Dict[str, Any]]:
    if not hostname:
        return None

    with get_db_session() as session:
        asset_row = _find_asset_by_public_identifier(session, hostname)
        if asset_row is None:
            return None

        asset = serialize_asset(asset_row)
        hostname = asset_row.hostname
        sessions = session.execute(
            select(SessionRecord)
            .where(SessionRecord.hostname == hostname)
            .order_by(SessionRecord.recorded_at.desc(), SessionRecord.id.desc())
            .limit(100)
        ).scalars().all()
        alerts = session.execute(
            select(Alert)
            .where(Alert.hostname == hostname)
            .order_by(Alert.timestamp.desc(), Alert.id.desc())
            .limit(100)
        ).scalars().all()
        app_history = session.execute(
            select(ActiveApplicationHistory)
            .where(ActiveApplicationHistory.hostname == hostname)
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .limit(100)
        ).scalars().all()
        hardware_changes = session.execute(
            select(HardwareChange)
            .where(HardwareChange.hostname == hostname)
            .order_by(HardwareChange.detected_at.desc(), HardwareChange.id.desc())
            .limit(100)
        ).scalars().all()
        asset_samples = session.execute(
            select(Asset)
            .where(Asset.id == asset_row.id)
        ).scalars().all()

        summary = _session_summary(session, hostname)
        asset.update(summary)
        asset.update(_alert_summary(session, hostname))
        asset.update(_activity_summary(session, hostname))

        timeline: List[Dict[str, Any]] = []
        ordered_sessions = sorted(sessions, key=lambda row: (row.recorded_at, row.id), reverse=True)
        for row in ordered_sessions:
            if row.event_type == "LOGIN":
                if _is_countable_login(row):
                    timeline.append(_timeline_event(row.login_timestamp or row.recorded_at, "Login", f"{row.username or 'Unknown user'} logged in", "LOW"))
            elif row.event_type == "LOGOUT":
                timeline.append(_timeline_event(row.logout_timestamp or row.recorded_at, "Logout", f"{row.username or 'Unknown user'} logged out", "LOW"))

        for row in alerts:
            details = row.details or {}
            description = details.get("description") or details.get("message") or f"{row.alert_type} detected"
            timeline.append(_timeline_event(row.timestamp, "Alert", description, row.severity))

        for row in hardware_changes:
            event_name = "RAM Change" if row.change_type == "RAM_CHANGE" else "Motherboard Change"
            timeline.append(_timeline_event(row.detected_at, event_name, f"{event_name} detected", row.severity))

        for row in app_history:
            app_name = row.application or row.window_title or row.process_path or "Application"
            timeline.append(_timeline_event(row.timestamp, "Application Started", f"{app_name} opened", "LOW"))

        if asset_row.last_seen:
            status_type = "Device Online" if asset["status"] == "Online" else "Device Offline"
            timeline.append(_timeline_event(asset_row.last_seen, status_type, f"{asset['status']} • Last seen {asset.get('last_seen_human') or asset.get('last_seen')}", None))

        timeline.sort(key=lambda item: _parse_datetime(item.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

        application_usage: Dict[str, int] = {}
        for row in app_history:
            name = row.application or "Unknown"
            application_usage[name] = application_usage.get(name, 0) + 1

        alert_trend: Dict[str, int] = {}
        for row in alerts:
            day = row.timestamp.astimezone(timezone.utc).date().isoformat()
            alert_trend[day] = alert_trend.get(day, 0) + 1

        login_frequency: Dict[str, int] = {}
        for row in sessions:
            if not _is_countable_login(row):
                continue
            stamp = row.login_timestamp or row.recorded_at
            day = stamp.astimezone(timezone.utc).date().isoformat()
            login_frequency[day] = login_frequency.get(day, 0) + 1

        cpu_history = [
            {"timestamp": _iso(row.collected_at), "value": _iso(row.cpu_usage_percent)}
            for row in reversed(asset_samples)
            if row.cpu_usage_percent is not None
        ]
        ram_history = [
            {"timestamp": _iso(row.collected_at), "value": _iso(row.ram_usage_percent)}
            for row in reversed(asset_samples)
            if row.ram_usage_percent is not None
        ]

        return {
            "asset": asset,
            "sessions": [serialize_session(row) for row in sessions],
            "alerts": [serialize_alert(row) for row in alerts],
            "application_timeline": [serialize_active_application_history(row) for row in app_history],
            "hardware_changes": [
                {
                    "hostname": row.hostname,
                    "change_type": row.change_type,
                    "severity": row.severity,
                    "previous_value": row.previous_value or {},
                    "current_value": row.current_value or {},
                    "difference": row.difference or {},
                    "detected_at": _iso(row.detected_at),
                }
                for row in hardware_changes
            ],
            "timeline": timeline[:200],
            "charts": {
                "cpu_usage_history": cpu_history,
                "ram_usage_history": ram_history,
                "login_frequency": [{"label": key, "value": value} for key, value in sorted(login_frequency.items())],
                "application_usage": [{"label": key, "value": value} for key, value in sorted(application_usage.items(), key=lambda item: item[1], reverse=True)[:10]],
                "alert_trend": [{"label": key, "value": value} for key, value in sorted(alert_trend.items())],
            },
        }


def _find_asset_row(session, record: Dict[str, Any], device_uid: str) -> Optional[Asset]:
    predicates = []
    for key, value in identity_candidates({**record, "device_uid": device_uid}):
        if key == "uuid":
            parsed_uuid = _parse_uuid(value)
            if parsed_uuid:
                predicates.append(Asset.uuid == parsed_uuid)
        elif key == "bios_serial":
            predicates.append(func.lower(Asset.bios_serial) == value)
        elif key == "baseboard_serial":
            predicates.append(func.lower(Asset.baseboard_serial) == value)
        elif key == "mac_address":
            predicates.append(func.lower(Asset.mac_address) == value)
        elif key == "composite_id":
            predicates.append(func.lower(Asset.composite_id) == value)
        elif key == "device_uid":
            predicates.append(Asset.device_uid == value)
    if not predicates:
        return None
    return session.execute(
        select(Asset)
        .where(or_(*predicates))
        .order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def _find_asset_by_public_identifier(session, identifier: str) -> Optional[Asset]:
    if not identifier:
        return None
    normalized = identifier.strip().lower()
    predicates = [
        Asset.device_uid == normalized,
        func.lower(Asset.hostname) == normalized,
        func.lower(Asset.bios_serial) == normalized,
        func.lower(Asset.baseboard_serial) == normalized,
        func.lower(Asset.composite_id) == normalized,
    ]
    parsed_uuid = _parse_uuid(identifier)
    if parsed_uuid:
        predicates.append(Asset.uuid == parsed_uuid)
    return session.execute(
        select(Asset)
        .where(or_(*predicates))
        .order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.asc())
        .limit(1)
    ).scalar_one_or_none()


def merge_duplicate_assets(session) -> int:
    rows = session.execute(
        select(Asset).order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.asc())
    ).scalars().all()
    owner_by_key: Dict[tuple[str, str], Asset] = {}
    duplicate_to_owner: Dict[int, Asset] = {}
    for row in rows:
        candidates = _asset_identity_candidates(row)
        owner = next((owner_by_key[key] for key in candidates if key in owner_by_key), None)
        if owner is None:
            for key in candidates:
                owner_by_key[key] = row
            continue
        duplicate_to_owner[row.id] = owner
        for key in candidates:
            owner_by_key[key] = owner

    rows_by_hostname: Dict[str, List[Asset]] = {}
    for row in rows:
        hostname_key = _clean_identity_value(row.hostname)
        if hostname_key:
            rows_by_hostname.setdefault(hostname_key, []).append(row)

    for hostname_rows in rows_by_hostname.values():
        live_rows = [row for row in hostname_rows if row.id not in duplicate_to_owner]
        if len(live_rows) < 2 or not _same_hostname_rows_are_safe_to_merge(live_rows):
            continue
        owner = sorted(
            live_rows,
            key=lambda row: (row.last_seen or row.collected_at or datetime.min.replace(tzinfo=timezone.utc), -(row.id or 0)),
            reverse=True,
        )[0]
        for duplicate in live_rows:
            if duplicate.id != owner.id:
                duplicate_to_owner[duplicate.id] = owner

    for duplicate_id, owner in duplicate_to_owner.items():
        duplicate = session.get(Asset, duplicate_id)
        if duplicate is None or duplicate.id == owner.id:
            continue
        _merge_asset_row(owner, duplicate)
        session.execute(
            HardwareChange.__table__.update()
            .where(HardwareChange.previous_asset_id == duplicate.id)
            .values(previous_asset_id=owner.id)
        )
        session.execute(
            HardwareChange.__table__.update()
            .where(HardwareChange.current_asset_id == duplicate.id)
            .values(current_asset_id=owner.id)
        )
        session.delete(duplicate)
    return len(duplicate_to_owner)


def _same_hostname_rows_are_safe_to_merge(rows: List[Asset]) -> bool:
    for field in ("uuid", "bios_serial", "baseboard_serial"):
        values = {
            _clean_identity_value(getattr(row, field))
            for row in rows
            if _clean_identity_value(getattr(row, field))
        }
        if len(values) > 1:
            return False
    return True


def _merge_asset_row(owner: Asset, duplicate: Asset) -> None:
    preferred = owner
    if duplicate.last_seen and (not owner.last_seen or duplicate.last_seen > owner.last_seen):
        preferred = duplicate
    for attr in (
        "hostname", "ip_address", "mac_address", "bios_serial", "baseboard_serial", "uuid",
        "composite_id", "cpu_name", "ram_total_gb", "baseboard_manufacturer",
        "baseboard_product", "windows_version", "current_website", "active_window_title",
        "active_process_path", "active_process_name", "cpu_usage_percent", "ram_usage_percent",
        "collection_method", "collection_errors", "collected_at", "last_seen",
    ):
        value = getattr(preferred, attr)
        if value not in (None, "", []):
            setattr(owner, attr, value)
