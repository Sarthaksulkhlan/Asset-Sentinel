import hashlib
import logging
import ctypes
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import delete, desc, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import get_db_session
from config import Config
from models import ActiveApplication, ActiveApplicationHistory, ActivitySession, Alert, ApplicationUsageDaily, ApplicationUsageSegment, Asset, Company, HardwareChange, SessionRecord


logger = logging.getLogger("asset_sentinel.storage")

REAL_LOGIN_SOURCES = {
    "windows_interactive_logon",
    "windows_session_observed",
    "windows_unlock",
    "windows_unlock_observed",
    "windows_session_reconnect",
}
REAL_LOGIN_EVENT_IDS = {"4624", "4801", "4778", "LOCKAPP_UNLOCK", "SESSION_OBSERVED"}
NON_COUNTABLE_LOGIN_SOURCES = {
    "windows_lock",
    "windows_lock_observed",
    "windows_session_disconnect",
}
SESSION_STATE_SOURCES = NON_COUNTABLE_LOGIN_SOURCES | {"windows_logoff", "windows_user_logoff"}
SESSION_STATE_EVENT_IDS = {"4800", "4801", "4779", "4778", "LOCKAPP_LOCK", "LOCKAPP_UNLOCK"}
DEFAULT_IDLE_THRESHOLD_SECONDS = int(os.environ.get("IDLE_THRESHOLD_SECONDS") or os.environ.get("ASSET_SENTINEL_IDLE_THRESHOLD_SECONDS", "60"))
DEFAULT_DEVELOPMENT_COMPANY_NAME = os.environ.get("ASSET_SENTINEL_DEFAULT_COMPANY", "Asset Sentinel Internal")


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


def _default_company_id(session) -> Optional[int]:
    preferred = session.execute(
        select(Company.id)
        .where(func.lower(Company.name) == DEFAULT_DEVELOPMENT_COMPANY_NAME.lower())
        .limit(1)
    ).scalar_one_or_none()
    if preferred is not None:
        return int(preferred)
    only_company = session.execute(
        select(Company.id)
        .order_by(Company.id.asc())
        .limit(1)
    ).scalar_one_or_none()
    return int(only_company) if only_company is not None else None


def _database_now(session) -> datetime:
    try:
        return _parse_required_datetime(session.execute(select(func.now())).scalar_one())
    except Exception:
        return datetime.now(timezone.utc)


def _company_id_for_hostname(session, hostname: Optional[str]) -> Optional[int]:
    if hostname:
        company_id = session.execute(
            select(Asset.company_id)
            .where(Asset.hostname == hostname)
            .where(Asset.company_id.is_not(None))
            .order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if company_id is not None:
            return int(company_id)
    return _default_company_id(session)


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


def _human_age(value: Optional[datetime], now: Optional[datetime] = None) -> Optional[str]:
    if not value:
        return None
    now = now or datetime.now(value.tzinfo or timezone.utc)
    if now.tzinfo and value.tzinfo:
        now = now.astimezone(value.tzinfo)
    raw_seconds = int((now - value).total_seconds())
    if raw_seconds < -Config.HEARTBEAT_FUTURE_SKEW_SECONDS:
        return "0 seconds ago"
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


def _status_from_last_seen(value: Optional[datetime], now: Optional[datetime] = None) -> str:
    if not value:
        logger.info(
            "Dashboard status calculation: last_seen=None threshold=%s status=Offline reason=no_heartbeat",
            Config.HEARTBEAT_TIMEOUT_SECONDS,
        )
        return "Offline"
    now = now or datetime.now(value.tzinfo or timezone.utc)
    if now.tzinfo and value.tzinfo:
        now = now.astimezone(value.tzinfo)
    seconds = (now - value).total_seconds()
    if seconds < -Config.HEARTBEAT_FUTURE_SKEW_SECONDS:
        logger.info(
            "Dashboard status calculation: last_seen=%s age_seconds=%s threshold=%s status=Online reason=future_clock_skew_grace",
            value.isoformat(),
            round(seconds, 3),
            Config.HEARTBEAT_TIMEOUT_SECONDS,
        )
        return "Online"
    if seconds <= max(1, Config.HEARTBEAT_TIMEOUT_SECONDS):
        logger.info(
            "Dashboard status calculation: last_seen=%s age_seconds=%s threshold=%s status=Online",
            value.isoformat(),
            round(seconds, 3),
            Config.HEARTBEAT_TIMEOUT_SECONDS,
        )
        return "Online"
    logger.info(
        "Dashboard status calculation: last_seen=%s age_seconds=%s threshold=%s status=Offline reason=heartbeat_timeout",
        value.isoformat(),
        round(seconds, 3),
        Config.HEARTBEAT_TIMEOUT_SECONDS,
    )
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


def serialize_asset(row: Asset, now: Optional[datetime] = None) -> Dict[str, Any]:
    live_status = _status_from_last_seen(row.last_seen, now)
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
        "last_seen_human": _human_age(row.last_seen, now),
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
        "company_id": row.company_id,
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


def list_assets(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db_session() as session:
        reference_now = _database_now(session)
        merge_duplicate_assets(session)
        query = select(Asset).order_by(Asset.hostname.asc())
        if company_id is not None:
            query = query.where(Asset.company_id == company_id)
        rows = session.execute(query).scalars().all()
        assets = []
        for row in rows:
            asset = serialize_asset(row, reference_now)
            asset.update(_session_summary(session, row.hostname, company_id))
            asset.update(_alert_summary(session, row.hostname, company_id))
            asset.update(_activity_summary(session, row.hostname, company_id))
            assets.append(asset)
        logger.info(
            "Dashboard assets query returned %s assets: online=%s offline=%s",
            len(assets),
            sum(1 for asset in assets if asset.get("status") == "Online"),
            sum(1 for asset in assets if asset.get("status") == "Offline"),
        )
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
    if record.get("last_seen"):
        incoming_last_seen = _parse_required_datetime(record.get("last_seen"))
        if (datetime.now(incoming_last_seen.tzinfo or timezone.utc) - incoming_last_seen).total_seconds() < -Config.HEARTBEAT_FUTURE_SKEW_SECONDS:
            incoming_last_seen = datetime.now(timezone.utc)
        if row.last_seen is None or incoming_last_seen > row.last_seen:
            row.last_seen = incoming_last_seen
    row.status = _status_from_last_seen(row.last_seen)
    row.collection_method = record.get("collection_method") or "none"
    row.collection_errors = record.get("collection_errors") or []
    row.collected_at = _parse_required_datetime(record.get("collected_at"))
    return row


def upsert_asset(record: Dict[str, Any]) -> None:
    device_uid = resolve_device_uid(record)
    with get_db_session() as session:
        company_id = record.get("company_id") or _company_id_for_hostname(session, record.get("hostname"))
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
        if company_id is not None:
            row.company_id = int(company_id)
        merge_duplicate_assets(session)


def ensure_asset_registered(record: Dict[str, Any]) -> str:
    device_uid = resolve_device_uid(record)
    upsert_asset(record)
    return device_uid


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


def list_alerts(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db_session() as session:
        query = select(Alert).order_by(Alert.timestamp.asc(), Alert.id.asc())
        if company_id is not None:
            query = query.where(Alert.company_id == company_id)
        rows = session.execute(query).scalars().all()
        return [serialize_alert(row) for row in rows]


def append_alert(alert_type: str, hostname: str, severity: str, details: Dict[str, Any], timestamp: Any = None) -> Dict[str, Any]:
    with get_db_session() as session:
        company_id = (details or {}).get("company_id") or _company_id_for_hostname(session, hostname)
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
                if existing.company_id is None and company_id is not None:
                    existing.company_id = int(company_id)
                return serialize_alert(existing)
        row = Alert(
            company_id=company_id,
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


def _session_summary(session, hostname: str, company_id: Optional[int] = None) -> Dict[str, Any]:
    query = select(SessionRecord).where(SessionRecord.hostname == hostname)
    if company_id is not None:
        query = query.where(SessionRecord.company_id == company_id)
    rows = session.execute(query.order_by(SessionRecord.recorded_at.asc(), SessionRecord.id.asc())).scalars().all()
    if not rows:
        logger.info("Dashboard login summary for hostname=%s: no login_history records", hostname)
        return {"logins_today": 0, "logins_this_week": 0, "total_logins": 0}

    countable_login_rows = [row for row in rows if _is_countable_login(row)]
    login_rows = _dedup_countable_login_rows(countable_login_rows)
    latest = rows[-1]
    ordered_login_rows = sorted(
        login_rows,
        key=lambda row: (
            _login_event_time(row) or datetime.min.replace(tzinfo=timezone.utc),
            row.id or 0,
        ),
        reverse=True,
    )
    latest_login = ordered_login_rows[0] if ordered_login_rows else latest
    current_open_login = _current_open_login(rows)
    active_login = current_open_login
    current_login = active_login or latest_login
    today = datetime.now(_local_tzinfo()).date()
    week_start = today - timedelta(days=today.weekday())
    logins_today = 0
    logins_this_week = 0
    last_successful_login = None
    last_failed_login = None
    last_logout = None
    for row in sorted(rows, key=lambda item: (_login_event_time(item) or datetime.min.replace(tzinfo=timezone.utc), item.id or 0)):
        stamp = row.login_timestamp or row.recorded_at
        stamp_date = _local_date(stamp) if stamp else None
        if row in login_rows:
            parsed_stamp = _login_event_time(row)
            if parsed_stamp and (last_successful_login is None or parsed_stamp > last_successful_login):
                last_successful_login = parsed_stamp
            if stamp_date == today:
                logins_today += 1
            if stamp_date and stamp_date >= week_start:
                logins_this_week += 1
        if row.event_type == "LOGOUT":
            last_logout = row.logout_timestamp or row.recorded_at
        details = getattr(row, "details", None) or {}
        if isinstance(details, dict) and details.get("failed_login_timestamp"):
            last_failed_login = _parse_datetime(details.get("failed_login_timestamp"))

    summary = {
        "current_user": current_login.username or latest_login.username,
        "username": current_login.username or latest_login.username,
        "session_id": current_login.session_id or latest_login.session_id,
        "login_timestamp": _iso(current_login.login_timestamp or current_login.recorded_at),
        "last_login": _iso(current_login.login_timestamp or current_login.recorded_at),
        "current_login_time": _iso(current_login.login_timestamp or current_login.recorded_at),
        "logout_timestamp": _iso(last_logout or latest.logout_timestamp),
        "last_logout": _iso(last_logout or latest.logout_timestamp),
        "session_duration": (
            _duration(active_login.login_timestamp or active_login.recorded_at)
            if active_login
            else (latest_login.session_duration or "Ended")
        ),
        "total_logins": len(login_rows),
        "logins_today": logins_today,
        "logins_this_week": logins_this_week,
        "last_successful_login": _iso(last_successful_login),
        "last_failed_login": _iso(last_failed_login),
        "active_session": bool(current_open_login),
    }
    logger.info(
        "Dashboard login summary for hostname=%s: total=%s today=%s week=%s last_success=%s",
        hostname,
        summary["total_logins"],
        summary["logins_today"],
        summary["logins_this_week"],
        summary["last_successful_login"],
    )
    return summary


def _alert_summary(session, hostname: str, company_id: Optional[int] = None) -> Dict[str, Any]:
    query = select(Alert).where(Alert.hostname == hostname)
    if company_id is not None:
        query = query.where(Alert.company_id == company_id)
    rows = session.execute(query.order_by(Alert.timestamp.desc()).limit(20)).scalars().all()
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
    if row.event_type != "LOGIN":
        return False
    if row.login_source in NON_COUNTABLE_LOGIN_SOURCES:
        return False
    if row.login_source in REAL_LOGIN_SOURCES:
        return True
    if str(row.windows_event_id or "") in REAL_LOGIN_EVENT_IDS:
        return True
    return False


def _is_lock_or_logout(row: SessionRecord) -> bool:
    if row.event_type == "LOGOUT":
        return True
    source = row.login_source or ""
    event_id = str(row.windows_event_id or "")
    return source in NON_COUNTABLE_LOGIN_SOURCES or event_id in {"4800", "4779", "LOCKAPP_LOCK"}


def _current_open_login(rows: Iterable[SessionRecord]) -> Optional[SessionRecord]:
    ordered_rows = sorted(
        list(rows),
        key=lambda row: (
            _parse_datetime(row.recorded_at) or _parse_datetime(row.login_timestamp) or datetime.min.replace(tzinfo=timezone.utc),
            row.id or 0,
        ),
    )
    for row in reversed(ordered_rows):
        if _is_lock_or_logout(row):
            return None
        if _is_countable_login(row) and not row.logout_timestamp:
            return row
    return None


def _login_event_time(row: SessionRecord) -> Optional[datetime]:
    return _parse_datetime(row.login_timestamp or row.recorded_at)


def _dedup_countable_login_rows(rows: Iterable[SessionRecord]) -> List[SessionRecord]:
    deduped: List[SessionRecord] = []
    seen_keys: set[tuple] = set()
    for row in sorted(
        list(rows),
        key=lambda item: (
            _login_event_time(item) or datetime.min.replace(tzinfo=timezone.utc),
            item.id or 0,
        ),
    ):
        stamp = _login_event_time(row)
        if not stamp:
            continue
        event_record_id = str(row.windows_event_record_id or "")
        if event_record_id:
            identity = (row.hostname, event_record_id)
        else:
            identity = (
                row.hostname,
                row.username,
                row.session_id,
                row.login_source,
                str(row.windows_event_id or ""),
                stamp.isoformat(),
            )
        if identity in seen_keys:
            continue
        deduped.append(row)
        seen_keys.add(identity)
    return deduped


def _record_login_event_time(record: Dict[str, Any]) -> Optional[datetime]:
    return _parse_datetime(record.get("login_timestamp") or record.get("recorded_at") or record.get("last_seen"))


def _record_logout_event_time(record: Dict[str, Any]) -> Optional[datetime]:
    return _parse_datetime(record.get("logout_timestamp") or record.get("recorded_at") or record.get("last_seen"))


def _is_countable_login_record(record: Dict[str, Any]) -> bool:
    if record.get("event_type") != "LOGIN":
        return False
    source = record.get("login_source")
    event_id = str(record.get("windows_event_id") or "")
    return source in REAL_LOGIN_SOURCES or event_id in REAL_LOGIN_EVENT_IDS


def _is_lock_or_logout_record(record: Dict[str, Any]) -> bool:
    if record.get("event_type") == "LOGOUT":
        return True
    source = record.get("login_source") or ""
    event_id = str(record.get("windows_event_id") or "")
    return source in SESSION_STATE_SOURCES or event_id in {"4800", "4779", "LOCKAPP_LOCK"}


def _close_active_login_rows(
    session,
    *,
    hostname: str,
    company_id: Optional[int],
    closed_at: datetime,
) -> int:
    query = (
        select(SessionRecord)
        .where(SessionRecord.hostname == hostname)
        .where(SessionRecord.event_type == "LOGIN")
        .where(SessionRecord.active.is_(True))
    )
    if company_id is not None:
        query = query.where(or_(SessionRecord.company_id == company_id, SessionRecord.company_id.is_(None)))
    rows = session.execute(query).scalars().all()
    closed = 0
    for row in rows:
        login_at = _parse_datetime(row.login_timestamp or row.recorded_at)
        if login_at and login_at > closed_at:
            continue
        row.logout_timestamp = closed_at
        row.session_duration = _duration(login_at or row.recorded_at, closed_at) or row.session_duration or "Ended"
        row.active = False
        row.device_status = None
        row.last_seen = closed_at
        if row.company_id is None and company_id is not None:
            row.company_id = int(company_id)
        closed += 1
    if closed:
        logger.info("Closed %s active login row(s) for hostname=%s at %s", closed, hostname, closed_at.isoformat())
    return closed


def _activity_summary(session, hostname: str, company_id: Optional[int] = None) -> Dict[str, Any]:
    query = select(ActiveApplicationHistory).where(ActiveApplicationHistory.hostname == hostname)
    if company_id is not None:
        query = query.where(ActiveApplicationHistory.company_id == company_id)
    history = session.execute(query.order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc()).limit(10)).scalars().all()
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
        for record in records:
            company_id = record.get("company_id") or _company_id_for_hostname(session, record.get("hostname"))
            if _is_lock_or_logout_record(record):
                closed_at = _record_logout_event_time(record) or _parse_datetime(record.get("recorded_at"))
                if closed_at:
                    _close_active_login_rows(
                        session,
                        hostname=record.get("hostname") or "Unknown",
                        company_id=company_id,
                        closed_at=closed_at,
                    )
            existing = _find_existing_session_record(session, record)
            if existing is None:
                session.add(_build_session_record(record, company_id))
                continue
            if existing.company_id is None and company_id is not None:
                existing.company_id = int(company_id)
            existing.logout_timestamp = _parse_datetime(record.get("logout_timestamp"))
            existing.session_duration = record.get("session_duration")
            existing.active = bool(record.get("active", False))
            existing.device_status = record.get("device_status")
            existing.last_seen = _parse_datetime(record.get("last_seen"))
            existing.login_source = record.get("login_source")
            existing.windows_event_id = str(record.get("windows_event_id")) if record.get("windows_event_id") else existing.windows_event_id
            existing.windows_event_record_id = (
                str(record.get("windows_event_record_id"))
                if record.get("windows_event_record_id")
                else existing.windows_event_record_id
            )


def _find_existing_session_record(session, record: Dict[str, Any]) -> Optional[SessionRecord]:
    event_record_id = record.get("windows_event_record_id")
    hostname = record.get("hostname") or "Unknown"
    if event_record_id:
        existing = session.execute(
            select(SessionRecord)
            .where(SessionRecord.hostname == hostname)
            .where(SessionRecord.windows_event_record_id == str(event_record_id))
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return existing
    recorded_at = _parse_datetime(record.get("recorded_at"))
    query = (
        select(SessionRecord)
        .where(SessionRecord.event_type == (record.get("event_type") or "LOGIN"))
        .where(SessionRecord.hostname == hostname)
        .where(SessionRecord.username == record.get("username"))
        .where(SessionRecord.session_id == record.get("session_id"))
    )
    if recorded_at:
        query = query.where(SessionRecord.recorded_at == recorded_at)
    return session.execute(query.limit(1)).scalar_one_or_none()


def _session_record_with_storage_time(record: Dict[str, Any], received_at: datetime) -> Dict[str, Any]:
    normalized = dict(record)
    received_iso = received_at.isoformat()
    normalized["recorded_at"] = normalized.get("recorded_at") or received_iso
    normalized["last_seen"] = (
        normalized.get("last_seen")
        or normalized.get("login_timestamp")
        or normalized.get("logout_timestamp")
        or received_iso
    )
    return normalized


def append_session(record: Dict[str, Any]) -> None:
    logger.info(
        "Telemetry before insert: type=%s hostname=%s username=%s event_id=%s record_id=%s",
        record.get("event_type") or "LOGIN",
        record.get("hostname"),
        record.get("username"),
        record.get("windows_event_id"),
        record.get("windows_event_record_id"),
    )
    with get_db_session() as session:
        record = _session_record_with_storage_time(record, _database_now(session))
        company_id = record.get("company_id") or _company_id_for_hostname(session, record.get("hostname"))
        event_record_id = record.get("windows_event_record_id")
        if event_record_id:
            existing = session.execute(
                select(SessionRecord)
                .where(SessionRecord.hostname == (record.get("hostname") or "Unknown"))
                .where(SessionRecord.windows_event_record_id == str(event_record_id))
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                if existing.company_id is None and company_id is not None:
                    existing.company_id = int(company_id)
                logger.info(
                    "Skipping duplicate session event: hostname=%s event_record_id=%s",
                    record.get("hostname"),
                    event_record_id,
                )
                return
        source = record.get("login_source")
        event_id = str(record.get("windows_event_id") or "")
        if record.get("event_type") == "LOGIN" and (
            record.get("login_source") not in REAL_LOGIN_SOURCES
            and event_id not in REAL_LOGIN_EVENT_IDS
            and source not in SESSION_STATE_SOURCES
            and event_id not in SESSION_STATE_EVENT_IDS
        ):
            logger.info(
                "Skipping non-login session event: host=%s source=%s event=%s",
                record.get("hostname"),
                record.get("login_source"),
                record.get("windows_event_id"),
            )
            return
        hostname = record.get("hostname") or "Unknown"
        if _is_lock_or_logout_record(record):
            closed_at = _record_logout_event_time(record) or _parse_required_datetime(record.get("recorded_at"))
            _close_active_login_rows(
                session,
                hostname=hostname,
                company_id=company_id,
                closed_at=closed_at,
            )
        elif _is_countable_login_record(record):
            login_at = _record_login_event_time(record) or _parse_required_datetime(record.get("recorded_at"))
            _close_active_login_rows(
                session,
                hostname=hostname,
                company_id=company_id,
                closed_at=login_at,
            )

        session.add(_build_session_record(record, company_id))
        session.flush()
        logger.info(
            "%s detected and inserted: hostname=%s username=%s event_id=%s record_id=%s",
            record.get("event_type") or "LOGIN",
            record.get("hostname"),
            record.get("username"),
            record.get("windows_event_id"),
            record.get("windows_event_record_id"),
        )


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


def activate_session_event(hostname: str, windows_event_record_id: Optional[str], last_seen: Optional[str] = None) -> bool:
    if not hostname or not windows_event_record_id:
        return False
    with get_db_session() as session:
        seen_at = _parse_datetime(last_seen) or datetime.now(timezone.utc)
        row = session.execute(
            select(SessionRecord)
            .where(SessionRecord.hostname == hostname)
            .where(SessionRecord.windows_event_record_id == str(windows_event_record_id))
            .limit(1)
        ).scalar_one_or_none()
        if row is None or not _is_countable_login(row):
            return False
        row.active = True
        row.logout_timestamp = None
        row.session_duration = "Active"
        row.last_seen = seen_at
        return True


def touch_active_session(hostname: str, username: Optional[str], session_id: Optional[str]) -> None:
    with get_db_session() as session:
        now = datetime.now(timezone.utc)
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


def _build_session_record(record: Dict[str, Any], company_id: Optional[int] = None) -> SessionRecord:
    return SessionRecord(
        company_id=company_id,
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


def list_active_applications_history(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db_session() as session:
        query = (
            select(ActiveApplicationHistory)
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .limit(500)
        )
        if company_id is not None:
            query = query.where(ActiveApplicationHistory.company_id == company_id)
        rows = session.execute(query).scalars().all()
        return [serialize_active_application_history(row) for row in rows]


def _latest_asset_device_id(session, hostname: str) -> str:
    row = session.execute(
        select(Asset)
        .where(Asset.hostname == hostname)
        .order_by(Asset.collected_at.desc(), Asset.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not row:
        return hostname
    return row.device_uid or row.composite_id or str(row.uuid or "") or row.hostname


def _event_idle_seconds(record: Dict[str, Any], duration_seconds: int) -> int:
    raw_idle = record.get("user_idle_seconds")
    threshold = int(record.get("idle_threshold_seconds") or DEFAULT_IDLE_THRESHOLD_SECONDS)
    try:
        idle_seconds = int(raw_idle)
    except (TypeError, ValueError):
        return 0
    if idle_seconds < threshold:
        return 0
    return max(0, min(duration_seconds, idle_seconds - threshold))


def _usage_day_start(value: datetime) -> datetime:
    return value.astimezone(Config.DISPLAY_TZINFO).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _increment_daily_usage(
    session,
    *,
    company_id: Optional[int] = None,
    hostname: str,
    username: Optional[str],
    application_name: str,
    window_title: Optional[str],
    start_time: datetime,
    end_time: datetime,
    foreground_seconds: int,
    active_seconds: int,
    idle_seconds: int,
    locked_seconds: int = 0,
) -> None:
    if foreground_seconds <= 0:
        return
    day = _usage_day_start(start_time)
    aggregate_username = username or "Unknown"
    stmt = pg_insert(ApplicationUsageDaily).values(
        company_id=company_id,
        date=day,
        hostname=hostname,
        username=aggregate_username,
        application_name=application_name,
        window_title=window_title,
        first_seen=start_time,
        last_seen=end_time,
        total_foreground_seconds=foreground_seconds,
        active_seconds=active_seconds,
        idle_seconds=idle_seconds,
        locked_seconds=locked_seconds,
    )
    session.execute(stmt.on_conflict_do_update(
        constraint="uq_application_usage_daily_app",
        set_={
            "company_id": func.coalesce(ApplicationUsageDaily.company_id, company_id),
            "first_seen": func.least(ApplicationUsageDaily.first_seen, start_time),
            "last_seen": func.greatest(ApplicationUsageDaily.last_seen, end_time),
            "total_foreground_seconds": ApplicationUsageDaily.total_foreground_seconds + foreground_seconds,
            "active_seconds": ApplicationUsageDaily.active_seconds + active_seconds,
            "idle_seconds": ApplicationUsageDaily.idle_seconds + idle_seconds,
            "locked_seconds": ApplicationUsageDaily.locked_seconds + locked_seconds,
            "updated_at": func.now(),
        },
    ))


def _record_usage_segment(session, previous: ActiveApplicationHistory, end_time: datetime, current_record: Dict[str, Any]) -> None:
    start_time = _parse_required_datetime(previous.timestamp)
    end_time = _parse_required_datetime(end_time)
    if end_time <= start_time:
        return
    duration_seconds = int((end_time - start_time).total_seconds())
    idle_seconds = _event_idle_seconds(current_record, duration_seconds)
    active_seconds = max(0, duration_seconds - idle_seconds)
    device_id = _latest_asset_device_id(session, previous.hostname)
    company_id = previous.company_id or _company_id_for_hostname(session, previous.hostname)
    app_name = previous.application or previous.window_title or previous.process_path or "Unknown"
    exists = session.execute(
        select(ApplicationUsageSegment.id)
        .where(
            ApplicationUsageSegment.company_id == company_id,
            ApplicationUsageSegment.device_id == device_id,
            ApplicationUsageSegment.application_name == app_name,
            ApplicationUsageSegment.start_time == start_time,
            ApplicationUsageSegment.end_time == end_time,
        )
        .limit(1)
    ).scalar_one_or_none()
    if exists:
        return
    session.add(ApplicationUsageSegment(
        company_id=company_id,
        device_id=device_id,
        hostname=previous.hostname,
        username=previous.username,
        application_name=app_name,
        window_title=previous.window_title,
        process_path=previous.process_path,
        start_time=start_time,
        end_time=end_time,
        active_duration=active_seconds,
        idle_duration=idle_seconds,
        date=start_time.replace(hour=0, minute=0, second=0, microsecond=0),
    ))


def _activity_state_from_record(record: Dict[str, Any]) -> str:
    if record.get("windows_locked"):
        return "LOCKED"
    if record.get("is_user_idle"):
        return "IDLE"
    return "ACTIVE"


def _same_activity_interval(row: ActivitySession, record: Dict[str, Any], created_date: datetime) -> bool:
    return (
        row.hostname == (record.get("hostname") or "Unknown")
        and (row.username or "Unknown") == (record.get("username") or "Unknown")
        and row.app_name == (record.get("application_name") or record.get("application") or "Unknown")
        and (row.window_title or "") == (record.get("window_title") or "")
        and _parse_required_datetime(row.created_date) == created_date
    )


def _apply_activity_delta(row: ActivitySession, seconds: int, state: str, threshold: int) -> None:
    seconds = max(0, int(seconds))
    if seconds <= 0:
        row.last_state = state
        return
    row.total_seconds = int(row.total_seconds or 0) + seconds
    if state == "LOCKED":
        row.locked_seconds = int(row.locked_seconds or 0) + seconds
    elif state == "IDLE":
        row.idle_seconds = int(row.idle_seconds or 0) + seconds
    else:
        row.active_seconds = int(row.active_seconds or 0) + seconds
    row.last_state = state


def record_activity_sample(record: Dict[str, Any]) -> None:
    sample_time = _parse_datetime(record.get("timestamp")) or datetime.now(timezone.utc)
    hostname = record.get("hostname") or "Unknown"
    username = record.get("username") or "Unknown"
    app_name = record.get("application_name") or record.get("application") or "Unknown"
    window_title = record.get("window_title") or "Unknown"
    state = _activity_state_from_record(record)
    threshold = int(record.get("idle_threshold_seconds") or DEFAULT_IDLE_THRESHOLD_SECONDS)
    created_date = _usage_day_start(sample_time)

    with get_db_session() as session:
        company_id = record.get("company_id") or _company_id_for_hostname(session, hostname)
        latest = session.execute(
            select(ActivitySession)
            .where(ActivitySession.hostname == hostname)
            .where(ActivitySession.company_id == company_id)
            .order_by(ActivitySession.end_time.desc(), ActivitySession.id.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest and _same_activity_interval(latest, record, created_date):
            latest_end = _parse_required_datetime(latest.end_time)
            delta = max(0, int((sample_time - latest_end).total_seconds()))
            _apply_activity_delta(latest, delta, state, threshold)
            latest.end_time = max(latest_end, sample_time)
            _increment_daily_usage(
                session,
                company_id=latest.company_id or company_id,
                hostname=latest.hostname,
                username=latest.username,
                application_name=latest.app_name,
                window_title=latest.window_title,
                start_time=latest_end,
                end_time=sample_time,
                foreground_seconds=delta,
                active_seconds=delta if state == "ACTIVE" else 0,
                idle_seconds=delta if state == "IDLE" else 0,
                locked_seconds=delta if state == "LOCKED" else 0,
            )
            return

        if latest:
            latest_end = _parse_required_datetime(latest.end_time)
            gap = max(0, int((sample_time - latest_end).total_seconds()))
            if gap:
                _apply_activity_delta(latest, gap, latest.last_state or "ACTIVE", threshold)
                latest.end_time = sample_time
                _increment_daily_usage(
                    session,
                    company_id=latest.company_id or company_id,
                    hostname=latest.hostname,
                    username=latest.username,
                    application_name=latest.app_name,
                    window_title=latest.window_title,
                    start_time=latest_end,
                    end_time=sample_time,
                    foreground_seconds=gap,
                    active_seconds=gap if latest.last_state == "ACTIVE" else 0,
                    idle_seconds=gap if latest.last_state == "IDLE" else 0,
                    locked_seconds=gap if latest.last_state == "LOCKED" else 0,
                )

        session.add(ActivitySession(
            company_id=company_id,
            hostname=hostname,
            username=username,
            app_name=app_name,
            window_title=window_title,
            start_time=sample_time,
            end_time=sample_time,
            total_seconds=0,
            active_seconds=0,
            idle_seconds=0,
            locked_seconds=0,
            created_date=created_date,
            last_state=state,
        ))


def record_activity_usage_aggregate(record: Dict[str, Any]) -> None:
    start_time = _parse_datetime(record.get("start_time"))
    end_time = _parse_datetime(record.get("end_time"))
    duration_seconds = int(record.get("duration_seconds") or 0)
    if not start_time or not end_time or duration_seconds <= 0:
        return
    if end_time <= start_time:
        end_time = start_time + timedelta(seconds=duration_seconds)

    hostname = record.get("hostname") or "Unknown"
    username = record.get("username") or "Unknown"
    app_name = record.get("application_name") or record.get("application") or "Unknown"
    window_title = record.get("window_title") or "Unknown"
    state = str(record.get("state") or "ACTIVE").upper()
    created_date = _usage_day_start(start_time)
    active_seconds = duration_seconds if state == "ACTIVE" else 0
    idle_seconds = duration_seconds if state == "IDLE" else 0
    locked_seconds = duration_seconds if state == "LOCKED" else 0

    with get_db_session() as session:
        company_id = record.get("company_id") or _company_id_for_hostname(session, hostname)
        latest = session.execute(
            select(ActivitySession)
            .where(ActivitySession.hostname == hostname)
            .where(ActivitySession.company_id == company_id)
            .where(ActivitySession.app_name == app_name)
            .where(ActivitySession.window_title == window_title)
            .where(ActivitySession.created_date == created_date)
            .order_by(ActivitySession.end_time.desc(), ActivitySession.id.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest and latest.last_state == state and _parse_required_datetime(latest.end_time) <= end_time:
            latest.total_seconds = int(latest.total_seconds or 0) + duration_seconds
            latest.active_seconds = int(latest.active_seconds or 0) + active_seconds
            latest.idle_seconds = int(latest.idle_seconds or 0) + idle_seconds
            latest.locked_seconds = int(latest.locked_seconds or 0) + locked_seconds
            latest.end_time = max(_parse_required_datetime(latest.end_time), end_time)
            latest.last_state = state
        else:
            session.add(ActivitySession(
                company_id=company_id,
                hostname=hostname,
                username=username,
                app_name=app_name,
                window_title=window_title,
                start_time=start_time,
                end_time=end_time,
                total_seconds=duration_seconds,
                active_seconds=active_seconds,
                idle_seconds=idle_seconds,
                locked_seconds=locked_seconds,
                created_date=created_date,
                last_state=state,
            ))

        _increment_daily_usage(
            session,
            company_id=company_id,
            hostname=hostname,
            username=username,
            application_name=app_name,
            window_title=window_title,
            start_time=start_time,
            end_time=end_time,
            foreground_seconds=duration_seconds,
            active_seconds=active_seconds,
            idle_seconds=idle_seconds,
            locked_seconds=locked_seconds,
        )


def append_active_application(record: Dict[str, Any]) -> None:
    event_timestamp = _parse_datetime(record.get("timestamp")) or datetime.now(timezone.utc)
    hostname = record.get("hostname") or "Unknown"
    username = record.get("username")
    application_name = record.get("application_name")
    executable_name = record.get("executable_name")
    window_title = record.get("window_title")
    logger.info(
        "Telemetry before insert: type=active_application hostname=%s username=%s application=%s window=%s timestamp=%s",
        hostname,
        username,
        application_name,
        window_title,
        record.get("timestamp"),
    )
    with get_db_session() as session:
        company_id = record.get("company_id") or _company_id_for_hostname(session, hostname)
        latest = session.execute(
            select(ActiveApplicationHistory)
            .where(ActiveApplicationHistory.hostname == hostname)
            .where(ActiveApplicationHistory.company_id == company_id)
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest and (
            latest.username == username
            and latest.application == application_name
            and latest.window_title == window_title
            and latest.process_path == (record.get("process_path") or record.get("active_process_path") or executable_name)
            and not record.get("activity_state_changed")
        ):
            logger.info(
                "Application event skipped as duplicate: hostname=%s application=%s window=%s",
                hostname,
                application_name,
                window_title,
            )
            return
        if latest:
            _record_usage_segment(session, latest, event_timestamp, record)
        row = ActiveApplication(
            company_id=company_id,
            hostname=hostname,
            username=username,
            application_name=application_name,
            executable_name=executable_name,
            window_title=window_title,
            timestamp=event_timestamp,
        )
        session.add(row)
        session.add(ActiveApplicationHistory(
            company_id=company_id,
            hostname=hostname,
            username=username,
            application=application_name,
            window_title=window_title,
            process_path=record.get("process_path") or record.get("active_process_path") or executable_name,
            timestamp=event_timestamp,
        ))
        session.flush()
        logger.info(
            "Application event inserted: hostname=%s username=%s application=%s window=%s timestamp=%s",
            hostname,
            username,
            application_name,
            window_title,
            event_timestamp.isoformat(),
        )
        old_rows = session.execute(
            select(ActiveApplicationHistory.id)
            .where(ActiveApplicationHistory.hostname == (record.get("hostname") or "Unknown"))
            .where(ActiveApplicationHistory.company_id == company_id)
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
    logger.info(
        "Telemetry before insert: type=heartbeat hostname=%s device_uid=%s cpu=%s ram=%s",
        hostname,
        (activity or {}).get("device_uid"),
        cpu_usage,
        ram_usage,
    )
    with get_db_session() as session:
        now = _database_now(session)
        lookup_record = {"hostname": hostname, **(activity or {})}
        company_id = lookup_record.get("company_id") or _company_id_for_hostname(session, hostname)
        row = _find_asset_row_for_heartbeat(session, hostname, company_id, lookup_record, lookup_record.get("device_uid") or "")
        if row is None:
            logger.warning("Heartbeat auto-registering missing asset for hostname=%s.", hostname)
            row = Asset(
                company_id=company_id,
                device_uid=resolve_device_uid(lookup_record),
                hostname=hostname or lookup_record.get("hostname") or "Unknown",
                collected_at=now,
            )
            session.add(row)
        elif row.company_id is None and company_id is not None:
            row.company_id = int(company_id)
        previous_last_seen = row.last_seen
        heartbeat_interval = (
            round((now - previous_last_seen).total_seconds(), 3)
            if previous_last_seen
            else None
        )
        row.last_seen = now
        row.status = "Online"
        row.collected_at = row.collected_at or now
        if cpu_usage is not None:
            row.cpu_usage_percent = cpu_usage
        if ram_usage is not None:
            row.ram_usage_percent = ram_usage
        if activity:
            row.active_process_name = activity.get("executable_name") or row.active_process_name
            row.active_window_title = activity.get("window_title") or row.active_window_title
            row.active_process_path = activity.get("process_path") or row.active_process_path
            row.current_website = activity.get("window_title") or row.current_website
        session.flush()
        logger.info(
            "Heartbeat received: hostname=%s heartbeat_timestamp=%s last_seen=%s interval_seconds=%s timeout_threshold=%s cpu=%s ram=%s active_app=%s",
            row.hostname,
            now.isoformat(),
            row.last_seen.isoformat() if row.last_seen else None,
            heartbeat_interval,
            Config.HEARTBEAT_TIMEOUT_SECONDS,
            cpu_usage,
            ram_usage,
            (activity or {}).get("application_name"),
        )
        logger.info(
            "Telemetry after insert: type=heartbeat hostname=%s device_uid=%s last_seen=%s",
            row.hostname,
            row.device_uid,
            row.last_seen.isoformat() if row.last_seen else None,
        )


def get_latest_active_applications(company_id: Optional[int] = None) -> List[Dict[str, Any]]:
    history = list_active_applications_history(company_id)
    latest_by_host: Dict[str, Dict[str, Any]] = {}
    for record in history:
        hostname = record.get("hostname")
        if hostname and hostname not in latest_by_host:
            latest_by_host[hostname] = record
    latest = list(latest_by_host.values())
    logger.info("Dashboard active applications query returned %s latest host records", len(latest))
    return latest


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
        result = serialize_active_application_history(row) if row else None
        logger.info("Dashboard latest active application query for hostname=%s found=%s", hostname, bool(result))
        return result


def get_asset_status(hostname: str) -> Optional[Dict[str, Any]]:
    with get_db_session() as session:
        reference_now = _database_now(session)
        row = _find_asset_by_public_identifier(session, hostname)
        if row is None:
            return None
        asset = serialize_asset(row, reference_now)
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


def _countable_login_times(sessions: Iterable[SessionRecord]) -> List[datetime]:
    login_times: List[datetime] = []
    for row in sessions:
        if row.event_type != "LOGIN" or not _is_countable_login(row):
            continue
        stamp = row.login_timestamp or row.recorded_at
        if stamp:
            login_times.append(_parse_required_datetime(stamp))
    return sorted(login_times)


def _latest_session_start(sessions: Iterable[SessionRecord]) -> Optional[datetime]:
    login_times = _countable_login_times(sessions)
    return login_times[-1] if login_times else None


def _latest_active_session_start(sessions: Iterable[SessionRecord]) -> Optional[datetime]:
    session_rows = list(sessions)
    current_open = _current_open_login(session_rows)
    if current_open:
        return _parse_datetime(current_open.login_timestamp or current_open.recorded_at)
    login_times: List[datetime] = []
    for row in session_rows:
        if row.event_type != "LOGIN" or not row.active or not _is_countable_login(row):
            continue
        stamp = row.login_timestamp or row.recorded_at
        if stamp:
            login_times.append(_parse_required_datetime(stamp))
    return sorted(login_times)[-1] if login_times else None


def _is_lock_app_label(*values: Any) -> bool:
    return any("lockapp" in str(value or "").lower() or "lock screen" in str(value or "").lower() for value in values)


def _latest_lock_or_logout_time(sessions: Iterable[SessionRecord]) -> Optional[datetime]:
    times: List[datetime] = []
    for row in sessions:
        if not _is_lock_or_logout(row):
            continue
        stamp = _parse_datetime(row.logout_timestamp or row.recorded_at or row.login_timestamp)
        if stamp:
            times.append(stamp)
    return sorted(times)[-1] if times else None


def _inferred_active_session_start(
    sessions: Iterable[SessionRecord],
    app_history: Optional[Iterable[ActiveApplicationHistory]] = None,
    activity_sessions: Optional[Iterable[ActivitySession]] = None,
    asset_last_seen: Any = None,
    now: Optional[datetime] = None,
) -> Optional[datetime]:
    session_rows = list(sessions)
    return _latest_active_session_start(session_rows)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def _local_user_idle_seconds() -> Optional[int]:
    try:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        tick_count = ctypes.windll.kernel32.GetTickCount()
        return max(0, int((tick_count - info.dwTime) / 1000))
    except Exception:
        return None


def _period_start(period: str, session_start: Optional[datetime], now: datetime) -> datetime:
    local_now = now.astimezone(Config.DISPLAY_TZINFO)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    if period == "current_session":
        return session_start or today_start
    if period == "yesterday":
        return today_start - timedelta(days=1)
    if period == "last_2_days":
        return today_start - timedelta(days=1)
    return today_start


def _event_time_candidates(
    sessions: Iterable[SessionRecord],
    app_history: Optional[Iterable[ActiveApplicationHistory]] = None,
    activity_sessions: Optional[Iterable[ActivitySession]] = None,
    asset_last_seen: Any = None,
) -> List[datetime]:
    candidates: List[datetime] = []
    for row in sessions:
        for stamp in (row.login_timestamp, row.logout_timestamp, row.last_seen, row.recorded_at):
            parsed = _parse_datetime(stamp)
            if parsed:
                candidates.append(parsed)
    for row in app_history or []:
        parsed = _parse_datetime(row.timestamp)
        if parsed:
            candidates.append(parsed)
    for row in activity_sessions or []:
        for stamp in (row.start_time, row.end_time):
            parsed = _parse_datetime(stamp)
            if parsed:
                candidates.append(parsed)
    parsed_last_seen = _parse_datetime(asset_last_seen)
    if parsed_last_seen:
        candidates.append(parsed_last_seen)
    return candidates


def _local_day_bounds(local_day) -> tuple[datetime, datetime]:
    start = datetime.combine(local_day, datetime.min.time(), tzinfo=Config.DISPLAY_TZINFO)
    end = start + timedelta(days=1)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _login_times_for_local_day(sessions: Iterable[SessionRecord], local_day) -> List[datetime]:
    login_times = []
    for row in sessions:
        if not _is_countable_login(row):
            continue
        stamp = _parse_datetime(row.login_timestamp or row.recorded_at)
        if stamp and stamp.astimezone(Config.DISPLAY_TZINFO).date() == local_day:
            login_times.append(stamp)
    return sorted(login_times)


def _session_window_for_local_days(
    local_days,
    sessions: Iterable[SessionRecord],
    app_history: Optional[Iterable[ActiveApplicationHistory]] = None,
    activity_sessions: Optional[Iterable[ActivitySession]] = None,
    asset_last_seen: Any = None,
    now: Optional[datetime] = None,
) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    session_rows = list(sessions)
    activity_rows = list(activity_sessions or [])
    app_rows = list(app_history or [])
    days = sorted(local_days)
    day_starts = [_local_day_bounds(day)[0] for day in days]
    day_ends = [_local_day_bounds(day)[1] for day in days]
    raw_start, raw_end = min(day_starts), min(max(day_ends), now)

    login_times = []
    for day in days:
        login_times.extend(_login_times_for_local_day(session_rows, day))

    candidates = [
        stamp
        for stamp in _event_time_candidates(session_rows, app_rows, activity_rows, asset_last_seen)
        if raw_start <= stamp <= raw_end
    ]
    started_at = min(login_times) if login_times else (min(candidates) if candidates else raw_start)
    ended_at = max(candidates) if candidates else started_at
    if ended_at < started_at:
        ended_at = started_at
    return started_at, min(ended_at, now)


def _period_bounds(
    period: str,
    sessions: Iterable[SessionRecord],
    now: Optional[datetime] = None,
    app_history: Optional[Iterable[ActiveApplicationHistory]] = None,
    activity_sessions: Optional[Iterable[ActivitySession]] = None,
    asset_last_seen: Any = None,
) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    local_now = now.astimezone(Config.DISPLAY_TZINFO)
    today = local_now.date()
    if period == "current_session":
        active_start = _inferred_active_session_start(sessions, app_history, activity_sessions, asset_last_seen, now)
        if active_start:
            return active_start, now
        return now, now
    if period == "yesterday":
        return _session_window_for_local_days([today - timedelta(days=1)], sessions, app_history, activity_sessions, asset_last_seen, now)
    if period == "last_2_days":
        return _session_window_for_local_days([today - timedelta(days=offset) for offset in range(1, -1, -1)], sessions, app_history, activity_sessions, asset_last_seen, now)
    return _session_window_for_local_days([today], sessions, app_history, activity_sessions, asset_last_seen, now)


def _period_end(period: str, now: datetime) -> datetime:
    local_now = now.astimezone(Config.DISPLAY_TZINFO)
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    if period == "yesterday":
        return today_start
    return now


def _new_usage_bucket(app_name: str, window_title: Optional[str] = None, process_path: Optional[str] = None) -> Dict[str, Any]:
    return {
        "label": app_name,
        "application_name": app_name,
        "value": 0,
        "total_duration_seconds": 0,
        "active_duration_seconds": 0,
        "productive_duration_seconds": 0,
        "idle_duration_seconds": 0,
        "locked_duration_seconds": 0,
        "percentage_of_session": 0,
        "window_title": window_title,
        "process_path": process_path,
        "last_seen_at": None,
    }


def _add_usage_duration(
    usage: Dict[str, Dict[str, Any]],
    app_name: str,
    foreground_seconds: int,
    idle_seconds: int,
    seen_at: datetime,
    locked_seconds: int = 0,
    window_title: Optional[str] = None,
    process_path: Optional[str] = None,
) -> None:
    foreground_seconds = max(0, int(foreground_seconds))
    locked_seconds = max(0, min(foreground_seconds, int(locked_seconds)))
    idle_seconds = max(0, min(foreground_seconds - locked_seconds, int(idle_seconds)))
    active_seconds = max(0, foreground_seconds - idle_seconds - locked_seconds)
    if foreground_seconds <= 0:
        return
    bucket = usage.setdefault(app_name, _new_usage_bucket(app_name, window_title, process_path))
    bucket["value"] += foreground_seconds
    bucket["total_duration_seconds"] += foreground_seconds
    bucket["active_duration_seconds"] += active_seconds
    bucket["productive_duration_seconds"] += active_seconds
    bucket["idle_duration_seconds"] += idle_seconds
    bucket["locked_duration_seconds"] += locked_seconds
    bucket["last_seen_at"] = _iso(seen_at)
    if window_title:
        bucket["window_title"] = window_title
    if process_path:
        bucket["process_path"] = process_path


def _locked_intervals(sessions: Iterable[SessionRecord], window_start: datetime, window_end: datetime) -> List[tuple[datetime, datetime]]:
    events = []
    for row in sessions:
        stamp = _parse_datetime(row.login_timestamp or row.logout_timestamp or row.recorded_at)
        if not stamp:
            continue
        source = row.login_source or ""
        event_id = str(row.windows_event_id or "")
        if source in {"windows_lock", "windows_lock_observed", "windows_session_disconnect"} or event_id in {"4800", "4779", "LOCKAPP_LOCK"}:
            events.append(("lock", stamp))
        elif source in {"windows_unlock", "windows_unlock_observed", "windows_session_reconnect"} or event_id in {"4801", "4778", "LOCKAPP_UNLOCK"}:
            events.append(("unlock", stamp))
        elif row.event_type == "LOGIN" and _is_countable_login(row):
            events.append(("unlock", stamp))
    events.sort(key=lambda item: item[1])

    intervals: List[tuple[datetime, datetime]] = []
    locked_at: Optional[datetime] = None
    for event_type, stamp in events:
        if event_type == "lock":
            locked_at = stamp
        elif event_type == "unlock" and locked_at:
            start = max(locked_at, window_start)
            end = min(stamp, window_end)
            if end > start:
                intervals.append((start, end))
            locked_at = None
    if locked_at:
        start = max(locked_at, window_start)
        if window_end > start:
            intervals.append((start, window_end))
    return intervals


def _overlap_seconds(start: datetime, end: datetime, intervals: Iterable[tuple[datetime, datetime]]) -> int:
    total = 0
    for locked_start, locked_end in intervals:
        overlap_start = max(start, locked_start)
        overlap_end = min(end, locked_end)
        if overlap_end > overlap_start:
            total += int((overlap_end - overlap_start).total_seconds())
    return total


def _application_usage_analytics(
    app_history: Iterable[ActiveApplicationHistory],
    session_start: Optional[datetime],
    activity_sessions: Optional[Iterable[ActivitySession]] = None,
    segments: Optional[Iterable[ApplicationUsageSegment]] = None,
    daily_usage: Optional[Iterable[ApplicationUsageDaily]] = None,
    period: str = "current_session",
    period_start_override: Optional[datetime] = None,
    period_end_override: Optional[datetime] = None,
    locked_intervals: Optional[Iterable[tuple[datetime, datetime]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    started_at = period_start_override or _period_start(period, session_start, now)
    ended_at = period_end_override or _period_end(period, now)
    session_duration = max(0, int((ended_at - started_at).total_seconds()))
    usage: Dict[str, Dict[str, Any]] = {}
    locked_intervals = list(locked_intervals or [])
    segment_keys = set()
    use_daily_usage = period != "current_session"
    latest_activity_end: Optional[datetime] = None

    for row in activity_sessions or []:
        start = _parse_datetime(row.start_time)
        end = _parse_datetime(row.end_time)
        if not start or not end or end <= started_at or start >= ended_at:
            continue
        latest_activity_end = max(latest_activity_end, end) if latest_activity_end else end
        clipped_start = max(start, started_at)
        clipped_end = min(end, ended_at)
        clipped_seconds = max(0, int((clipped_end - clipped_start).total_seconds()))
        original_seconds = max(1, int((end - start).total_seconds()))
        ratio = clipped_seconds / original_seconds
        _add_usage_duration(
            usage,
            row.app_name or "Unknown",
            clipped_seconds,
            int((row.idle_seconds or 0) * ratio),
            clipped_start,
            locked_seconds=int((row.locked_seconds or 0) * ratio),
            window_title=row.window_title,
        )

    has_activity_sessions = bool(usage)

    for row in daily_usage or []:
        if not use_daily_usage or has_activity_sessions:
            continue
        day = _parse_datetime(row.date)
        if not day or day < _usage_day_start(started_at) or day > _usage_day_start(ended_at):
            continue
        app_name = row.application_name or "Unknown"
        foreground = int(row.total_foreground_seconds or 0)
        locked = int(row.locked_seconds or 0)
        idle = int(row.idle_seconds or 0)
        _add_usage_duration(
            usage,
            app_name,
            foreground,
            idle,
            _parse_datetime(row.last_seen) or started_at,
            locked_seconds=locked,
            window_title=row.window_title,
        )

    has_daily_usage = bool(usage)

    for segment in segments or []:
        if has_daily_usage or has_activity_sessions:
            continue
        start = _parse_datetime(segment.start_time)
        end = _parse_datetime(segment.end_time)
        if not start or not end or end <= started_at or start >= ended_at:
            continue
        segment_keys.add((segment.application_name or "Unknown", int(start.timestamp()), int(end.timestamp())))
        clipped_start = max(start, started_at)
        clipped_end = min(end, ended_at)
        clipped_seconds = max(0, int((clipped_end - clipped_start).total_seconds()))
        original_seconds = max(1, int((end - start).total_seconds()))
        ratio = clipped_seconds / original_seconds
        locked_seconds = _overlap_seconds(clipped_start, clipped_end, locked_intervals)
        idle_seconds = min(clipped_seconds - locked_seconds, int((segment.idle_duration or 0) * ratio))
        _add_usage_duration(
            usage,
            segment.application_name or "Unknown",
            clipped_seconds,
            idle_seconds,
            clipped_start,
            locked_seconds=locked_seconds,
            window_title=segment.window_title,
            process_path=segment.process_path,
        )

    events = []
    for row in app_history:
        stamp = _parse_datetime(row.timestamp)
        if not stamp:
            continue
        app_name = row.application or row.window_title or row.process_path or "Unknown"
        events.append({
            "application_name": app_name,
            "window_title": row.window_title,
            "process_path": row.process_path,
            "timestamp": stamp,
        })

    events.sort(key=lambda item: item["timestamp"])
    for index, event in enumerate(events):
        raw_start = event["timestamp"]
        raw_end = events[index + 1]["timestamp"] if index + 1 < len(events) else ended_at
        if raw_end <= started_at or raw_start >= ended_at:
            continue
        if has_activity_sessions and latest_activity_end and raw_end <= latest_activity_end:
            continue
        start = max(raw_start, started_at, latest_activity_end if has_activity_sessions and latest_activity_end else started_at)
        end = min(raw_end, ended_at)
        seconds = max(0, int((end - start).total_seconds()))
        if seconds <= 0:
            continue
        app_name = event["application_name"]
        interval_key = (app_name, int(raw_start.timestamp()), int(raw_end.timestamp()))
        is_live_interval = index + 1 >= len(events)
        if interval_key in segment_keys or (has_daily_usage and not is_live_interval):
            continue
        live_idle_seconds = _local_user_idle_seconds() if index + 1 >= len(events) and ended_at == now else None
        locked_seconds = _overlap_seconds(start, end, locked_intervals)
        idle_seconds = 0
        if live_idle_seconds is not None and live_idle_seconds >= DEFAULT_IDLE_THRESHOLD_SECONDS:
            idle_seconds = min(seconds - locked_seconds, live_idle_seconds - DEFAULT_IDLE_THRESHOLD_SECONDS)
        _add_usage_duration(
            usage,
            app_name,
            seconds,
            idle_seconds,
            event["timestamp"],
            locked_seconds=locked_seconds,
            window_title=event.get("window_title"),
            process_path=event.get("process_path"),
        )

    denominator = max(session_duration, sum(item["total_duration_seconds"] for item in usage.values()), 1)
    items = sorted(usage.values(), key=lambda item: item["total_duration_seconds"], reverse=True)
    for item in items:
        item["percentage_of_session"] = round((item["total_duration_seconds"] / denominator) * 100, 2)
    total_foreground = sum(item["total_duration_seconds"] for item in usage.values())
    active_seconds = sum(item["active_duration_seconds"] for item in usage.values())
    idle_seconds = sum(item["idle_duration_seconds"] for item in usage.values())
    locked_seconds = max(
        sum(item["locked_duration_seconds"] for item in usage.values()),
        _overlap_seconds(started_at, ended_at, locked_intervals),
    )
    locked_seconds = min(session_duration, locked_seconds)
    if active_seconds + idle_seconds + locked_seconds > session_duration:
        overflow = active_seconds + idle_seconds + locked_seconds - session_duration
        idle_reduction = min(idle_seconds, overflow)
        idle_seconds -= idle_reduction
        overflow -= idle_reduction
        active_seconds = max(0, active_seconds - overflow)
    productivity_percentage = round((active_seconds / max(session_duration, 1)) * 100, 2)

    return {
        "items": items[:10],
        "session_started_at": _iso(started_at),
        "last_updated_at": _iso(ended_at),
        "total_session_duration_seconds": session_duration,
        "total_foreground_duration_seconds": total_foreground,
        "active_working_seconds": active_seconds,
        "idle_seconds": idle_seconds,
        "locked_seconds": locked_seconds,
        "productivity_percentage": productivity_percentage,
    }


def get_asset_details(hostname: str, company_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if not hostname:
        return None

    with get_db_session() as session:
        reference_now = _database_now(session)
        asset_row = _find_asset_by_public_identifier(session, hostname)
        if asset_row is None:
            return None
        if company_id is not None and asset_row.company_id != company_id:
            return None

        asset = serialize_asset(asset_row, reference_now)
        hostname = asset_row.hostname
        sessions_query = select(SessionRecord).where(SessionRecord.hostname == hostname)
        sessions_usage_query = select(SessionRecord).where(SessionRecord.hostname == hostname)
        alerts_query = select(Alert).where(Alert.hostname == hostname)
        app_history_query = select(ActiveApplicationHistory).where(ActiveApplicationHistory.hostname == hostname)
        app_history_usage_query = select(ActiveApplicationHistory).where(ActiveApplicationHistory.hostname == hostname)
        usage_segments_query = select(ApplicationUsageSegment).where(ApplicationUsageSegment.hostname == hostname)
        daily_usage_query = select(ApplicationUsageDaily).where(ApplicationUsageDaily.hostname == hostname)
        activity_sessions_query = select(ActivitySession).where(ActivitySession.hostname == hostname)
        hardware_changes_query = select(HardwareChange).where(HardwareChange.hostname == hostname)
        asset_samples_query = select(Asset).where(Asset.id == asset_row.id)
        if company_id is not None:
            sessions_query = sessions_query.where(SessionRecord.company_id == company_id)
            sessions_usage_query = sessions_usage_query.where(SessionRecord.company_id == company_id)
            alerts_query = alerts_query.where(Alert.company_id == company_id)
            app_history_query = app_history_query.where(ActiveApplicationHistory.company_id == company_id)
            app_history_usage_query = app_history_usage_query.where(ActiveApplicationHistory.company_id == company_id)
            usage_segments_query = usage_segments_query.where(ApplicationUsageSegment.company_id == company_id)
            daily_usage_query = daily_usage_query.where(ApplicationUsageDaily.company_id == company_id)
            activity_sessions_query = activity_sessions_query.where(ActivitySession.company_id == company_id)
            hardware_changes_query = hardware_changes_query.where(HardwareChange.company_id == company_id)
            asset_samples_query = asset_samples_query.where(Asset.company_id == company_id)

        sessions = session.execute(sessions_query.order_by(SessionRecord.recorded_at.desc(), SessionRecord.id.desc()).limit(100)).scalars().all()
        sessions_for_usage = session.execute(sessions_usage_query.order_by(SessionRecord.recorded_at.desc(), SessionRecord.id.desc()).limit(2000)).scalars().all()
        alerts = session.execute(alerts_query.order_by(Alert.timestamp.desc(), Alert.id.desc()).limit(100)).scalars().all()
        app_history = session.execute(app_history_query.order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc()).limit(100)).scalars().all()
        app_history_for_usage = session.execute(app_history_usage_query.order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc()).limit(2000)).scalars().all()
        usage_segments = session.execute(usage_segments_query.order_by(ApplicationUsageSegment.start_time.desc(), ApplicationUsageSegment.id.desc()).limit(5000)).scalars().all()
        daily_usage = session.execute(daily_usage_query.order_by(ApplicationUsageDaily.date.desc(), ApplicationUsageDaily.last_seen.desc(), ApplicationUsageDaily.id.desc()).limit(1000)).scalars().all()
        activity_session_rows = session.execute(activity_sessions_query.order_by(ActivitySession.created_date.desc(), ActivitySession.end_time.desc(), ActivitySession.id.desc()).limit(5000)).scalars().all()
        hardware_changes = session.execute(hardware_changes_query.order_by(HardwareChange.detected_at.desc(), HardwareChange.id.desc()).limit(100)).scalars().all()
        asset_samples = session.execute(asset_samples_query).scalars().all()

        summary = _session_summary(session, hostname, company_id)
        asset.update(summary)
        asset.update(_alert_summary(session, hostname, company_id))
        asset.update(_activity_summary(session, hostname, company_id))

        inferred_active_start = _inferred_active_session_start(
            sessions_for_usage,
            app_history_for_usage,
            activity_session_rows,
            asset_row.last_seen,
            reference_now,
        )
        if inferred_active_start and not asset.get("active_session"):
            inferred_iso = _iso(inferred_active_start)
            asset["active_session"] = True
            asset["login_timestamp"] = inferred_iso
            asset["last_login"] = inferred_iso
            asset["current_login_time"] = inferred_iso
            asset["session_duration"] = _duration(inferred_active_start, reference_now) or asset.get("session_duration")
            last_success = _parse_datetime(asset.get("last_successful_login"))
            if last_success is None or inferred_active_start > last_success:
                asset["last_successful_login"] = inferred_iso

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

        session_start = _latest_session_start(sessions_for_usage)
        usage_periods = {}
        for period in ("current_session", "today", "yesterday", "last_2_days"):
            period_start, period_end = _period_bounds(
                period,
                sessions_for_usage,
                app_history=app_history_for_usage,
                activity_sessions=activity_session_rows,
                asset_last_seen=asset_row.last_seen,
            )
            usage_periods[period] = _application_usage_analytics(
                app_history_for_usage,
                session_start,
                activity_session_rows,
                usage_segments,
                daily_usage,
                period,
                period_start,
                period_end,
                _locked_intervals(sessions_for_usage, period_start, period_end),
            )
        usage_analytics = usage_periods["today"]

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

        result = {
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
                "application_usage": usage_analytics["items"],
                "application_usage_summary": {
                    "total_session_duration_seconds": usage_analytics["total_session_duration_seconds"],
                    "session_started_at": usage_analytics["session_started_at"],
                    "last_updated_at": usage_analytics["last_updated_at"],
                    "total_foreground_duration_seconds": usage_analytics["total_foreground_duration_seconds"],
                    "active_working_seconds": usage_analytics["active_working_seconds"],
                    "idle_seconds": usage_analytics["idle_seconds"],
                    "locked_seconds": usage_analytics["locked_seconds"],
                    "productivity_percentage": usage_analytics["productivity_percentage"],
                },
                "application_usage_periods": {
                    key: {
                        "items": value["items"],
                        "summary": {
                            "total_session_duration_seconds": value["total_session_duration_seconds"],
                            "session_started_at": value["session_started_at"],
                            "last_updated_at": value["last_updated_at"],
                            "total_foreground_duration_seconds": value["total_foreground_duration_seconds"],
                            "active_working_seconds": value["active_working_seconds"],
                            "idle_seconds": value["idle_seconds"],
                            "locked_seconds": value["locked_seconds"],
                            "productivity_percentage": value["productivity_percentage"],
                        },
                    }
                    for key, value in usage_periods.items()
                },
                "alert_trend": [{"label": key, "value": value} for key, value in sorted(alert_trend.items())],
            },
        }
        logger.info(
            "Dashboard detail query for hostname=%s: sessions=%s app_events=%s timeline=%s logins_today=%s logins_week=%s",
            hostname,
            len(sessions),
            len(app_history),
            len(timeline[:200]),
            summary.get("logins_today"),
            summary.get("logins_this_week"),
        )
        return result


def get_device_health(identifier: str) -> Optional[Dict[str, Any]]:
    if not identifier:
        return None
    with get_db_session() as session:
        reference_now = _database_now(session)
        asset_row = _find_asset_by_public_identifier(session, identifier)
        if asset_row is None:
            return None
        asset = serialize_asset(asset_row, reference_now)
        hostname = asset_row.hostname
        latest_session = session.execute(
            select(SessionRecord)
            .where(SessionRecord.hostname == hostname)
            .order_by(SessionRecord.recorded_at.desc(), SessionRecord.id.desc())
            .limit(5)
        ).scalars().all()
        latest_application = session.execute(
            select(ActiveApplicationHistory)
            .where(ActiveApplicationHistory.hostname == hostname)
            .order_by(ActiveApplicationHistory.timestamp.desc(), ActiveApplicationHistory.id.desc())
            .limit(5)
        ).scalars().all()
        latest_alerts = session.execute(
            select(Alert)
            .where(Alert.hostname == hostname)
            .order_by(Alert.timestamp.desc(), Alert.id.desc())
            .limit(5)
        ).scalars().all()
        return {
            "registration": {
                "registered": True,
                "hostname": asset_row.hostname,
                "device_uid": asset_row.device_uid,
                "collection_method": asset_row.collection_method,
                "collected_at": _iso(asset_row.collected_at),
            },
            "last_heartbeat": {
                "last_seen": asset.get("last_seen"),
                "last_seen_human": asset.get("last_seen_human"),
                "status": asset.get("status"),
                "heartbeat_timeout_seconds": Config.HEARTBEAT_TIMEOUT_SECONDS,
                "cpu_usage": asset.get("cpu_usage"),
                "ram_usage": asset.get("ram_usage"),
            },
            "latest_telemetry": {
                "sessions": [serialize_session(row) for row in latest_session],
                "active_applications": [serialize_active_application_history(row) for row in latest_application],
                "alerts": [serialize_alert(row) for row in latest_alerts],
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


def _find_asset_row_for_heartbeat(
    session,
    hostname: Optional[str],
    company_id: Optional[int],
    record: Dict[str, Any],
    device_uid: str,
) -> Optional[Asset]:
    if hostname:
        query = select(Asset).where(Asset.hostname == hostname)
        if company_id is not None:
            query = query.where(Asset.company_id == company_id)
        row = session.execute(
            query.order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is not None:
            return row

    row = _find_asset_row(session, record, device_uid)
    if row is not None:
        return row

    if not hostname:
        return None

    return session.execute(
        select(Asset)
        .where(Asset.hostname == hostname)
        .order_by(Asset.last_seen.desc().nullslast(), Asset.collected_at.desc(), Asset.id.desc())
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
    if owner.company_id is None and duplicate.company_id is not None:
        owner.company_id = duplicate.company_id
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
    owner.status = _status_from_last_seen(owner.last_seen)
