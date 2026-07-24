import os
import time
from functools import wraps
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from storage import (
    activate_session_event,
    append_active_application,
    append_alert,
    append_session,
    find_asset_for_registration,
    get_latest_active_application_for_host,
    has_session_event_signature,
    list_active_applications_history,
    list_alerts,
    list_assets,
    list_sessions,
    record_activity_sample,
    record_activity_usage_aggregates,
    record_hardware_change,
    replace_sessions,
    resolve_device_uid,
    touch_active_session,
    update_asset_heartbeat,
    upsert_asset,
)
from pairing import pair_device, pairing_status


agent_api = Blueprint("agent_api", __name__, url_prefix="/api/agent")
DEFAULT_DEVELOPMENT_AGENT_TOKEN = "asset-sentinel-development-agent-token"
logger = logging.getLogger("asset_sentinel.agent_api")


def _agent_token() -> Optional[str]:
    return os.environ.get("ASSET_SENTINEL_AGENT_TOKEN") or os.environ.get("AGENT_TOKEN") or DEFAULT_DEVELOPMENT_AGENT_TOKEN


def _json_payload() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _parse_event_timestamp(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def require_agent_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        started_at = time.monotonic()
        expected = _agent_token()
        if not expected:
            return jsonify({"error": "Agent token is not configured"}), 503
        auth_header = request.headers.get("Authorization") or ""
        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or token != expected:
            return jsonify({"error": "Unauthorized agent request"}), 401
        response = fn(*args, **kwargs)
        elapsed_seconds = time.monotonic() - started_at
        if elapsed_seconds >= 1.0:
            logger.info(
                "Slow agent request: method=%s path=%s elapsed_seconds=%.3f",
                request.method,
                request.path,
                elapsed_seconds,
            )
        return response

    return wrapper


def _find_existing_asset(device_uid: str, hostname: Optional[str]) -> Optional[Dict[str, Any]]:
    return find_asset_for_registration(device_uid, hostname)


def _record_hardware_change_if_needed(existing: Optional[Dict[str, Any]], current: Dict[str, Any]) -> None:
    if not existing:
        return
    hostname = current.get("hostname") or existing.get("hostname") or "Unknown"
    detected_at = current.get("collected_at")
    previous_ram = existing.get("ram_total_gb")
    current_ram = current.get("ram_total_gb")
    if previous_ram is not None and current_ram is not None and float(previous_ram) != float(current_ram):
        details = {
            "previous_ram_gb": previous_ram,
            "current_ram_gb": current_ram,
            "previous_snapshot_time": existing.get("collected_at"),
            "current_snapshot_time": detected_at,
        }
        append_alert("RAM_CHANGE", hostname, "HIGH", details, detected_at)
        record_hardware_change(
            hostname,
            "RAM_CHANGE",
            "HIGH",
            {"ram_total_gb": previous_ram},
            {"ram_total_gb": current_ram},
            {"changed": True},
            detected_at,
        )

    motherboard_fields = ("bios_serial", "baseboard_serial", "uuid", "baseboard_product")
    differences = {}
    for field in motherboard_fields:
        previous_value = existing.get(field)
        current_value = current.get(field)
        if not previous_value or not current_value:
            continue
        if str(previous_value).strip().lower() != str(current_value).strip().lower():
            differences[field] = {"previous": previous_value, "current": current_value}
    if differences:
        append_alert("MOTHERBOARD_CHANGE", hostname, "CRITICAL", differences, detected_at)
        record_hardware_change(
            hostname,
            "MOTHERBOARD_CHANGE",
            "CRITICAL",
            {field: values["previous"] for field, values in differences.items()},
            {field: values["current"] for field, values in differences.items()},
            differences,
            detected_at,
        )


@agent_api.route("/register", methods=["POST"])
@require_agent_token
def register_asset():
    payload = _json_payload()
    device_uid = resolve_device_uid(payload)
    _record_hardware_change_if_needed(_find_existing_asset(device_uid, payload.get("hostname")), payload)
    upsert_asset(payload)
    return jsonify({"ok": True, "device_uid": device_uid})


@agent_api.route("/pairing/status", methods=["POST"])
@require_agent_token
def device_pairing_status():
    return jsonify(pairing_status(_json_payload()))


@agent_api.route("/pair", methods=["POST"])
@require_agent_token
def pair_agent_device():
    data, status_code = pair_device(_json_payload())
    return jsonify(data), status_code


@agent_api.route("/heartbeat", methods=["POST"])
@require_agent_token
def heartbeat():
    payload = _json_payload()
    activity = payload.get("current_active_application")
    if activity is not None and not isinstance(activity, dict):
        activity = None
    if isinstance(activity, dict):
        activity = {**activity}
        activity.setdefault("device_uid", payload.get("device_uid"))
    else:
        activity = {"device_uid": payload.get("device_uid")} if payload.get("device_uid") else None
    update_asset_heartbeat(
        payload.get("hostname"),
        payload.get("cpu_usage_percent"),
        payload.get("ram_usage_percent"),
        activity,
    )
    return jsonify({"ok": True})


@agent_api.route("/session", methods=["POST"])
@require_agent_token
def session_event():
    payload = _json_payload()
    append_session(payload)
    return jsonify({"ok": True})


@agent_api.route("/sessions", methods=["GET"])
@require_agent_token
def sessions():
    return jsonify(list_sessions())


@agent_api.route("/sessions/replace", methods=["POST"])
@require_agent_token
def replace_session_events():
    payload = _json_payload()
    records = payload.get("sessions")
    replace_sessions(records if isinstance(records, list) else [])
    return jsonify({"ok": True, "count": len(records) if isinstance(records, list) else 0})


@agent_api.route("/application", methods=["POST"])
@require_agent_token
def application_event():
    payload = _json_payload()
    record_activity_sample(payload)
    append_active_application(payload)
    return jsonify({"ok": True})


@agent_api.route("/application-event", methods=["POST"])
@require_agent_token
def application_history_event():
    received_at = datetime.now(timezone.utc)
    payload = _json_payload()
    event_timestamp = _parse_event_timestamp(payload.get("timestamp"))
    write_started_at = time.monotonic()
    append_active_application(payload)
    write_elapsed = time.monotonic() - write_started_at
    total_elapsed = (datetime.now(timezone.utc) - received_at).total_seconds()
    receive_lag = (received_at - event_timestamp).total_seconds() if event_timestamp else None
    logger.info(
        "Active application pipeline: hostname=%s application=%s event_timestamp=%s receive_lag_seconds=%s db_write_seconds=%.3f response_seconds=%.3f",
        payload.get("hostname"),
        payload.get("application_name") or payload.get("application"),
        payload.get("timestamp"),
        round(receive_lag, 3) if receive_lag is not None else None,
        write_elapsed,
        total_elapsed,
    )
    return jsonify({"ok": True})


@agent_api.route("/activity-sample", methods=["POST"])
@require_agent_token
def activity_sample():
    record_activity_sample(_json_payload())
    return jsonify({"ok": True})


@agent_api.route("/activity-usage", methods=["POST"])
@require_agent_token
def activity_usage():
    payload = _json_payload()
    records = payload.get("records")
    if not isinstance(records, list):
        records = []
    saved = record_activity_usage_aggregates(record for record in records if isinstance(record, dict))
    return jsonify({"ok": True, "count": saved})


@agent_api.route("/alert", methods=["POST"])
@require_agent_token
def alert_event():
    payload = _json_payload()
    result = append_alert(
        payload.get("alert_type"),
        payload.get("hostname"),
        payload.get("severity") or "LOW",
        payload.get("details") or {},
        payload.get("timestamp"),
    )
    return jsonify({"ok": True, "alert": result})


@agent_api.route("/alerts", methods=["GET"])
@require_agent_token
def alerts():
    return jsonify(list_alerts())


@agent_api.route("/assets", methods=["GET"])
@require_agent_token
def assets():
    return jsonify(list_assets())


@agent_api.route("/hardware-change", methods=["POST"])
@require_agent_token
def hardware_change():
    payload = _json_payload()
    record_hardware_change(
        hostname=payload.get("hostname"),
        change_type=payload.get("change_type"),
        severity=payload.get("severity") or "LOW",
        previous_value=payload.get("previous_value") or {},
        current_value=payload.get("current_value") or {},
        difference=payload.get("difference") or {},
        detected_at=payload.get("detected_at"),
    )
    return jsonify({"ok": True})


@agent_api.route("/session/exists", methods=["GET"])
@require_agent_token
def session_exists():
    return jsonify({
        "exists": has_session_event_signature(
            request.args.get("hostname") or "",
            request.args.get("windows_event_record_id"),
        )
    })


@agent_api.route("/session/activate", methods=["POST"])
@require_agent_token
def activate_session():
    payload = _json_payload()
    updated = activate_session_event(
        payload.get("hostname") or "",
        payload.get("windows_event_record_id"),
        payload.get("last_seen"),
    )
    return jsonify({"ok": True, "updated": updated})


@agent_api.route("/session/touch", methods=["POST"])
@require_agent_token
def touch_session():
    payload = _json_payload()
    touch_active_session(payload.get("hostname"), payload.get("username"), payload.get("session_id"))
    return jsonify({"ok": True})


@agent_api.route("/applications/history", methods=["GET"])
@require_agent_token
def applications_history():
    return jsonify(list_active_applications_history())


@agent_api.route("/applications/latest/<path:hostname>", methods=["GET"])
@require_agent_token
def latest_application(hostname: str):
    return jsonify(get_latest_active_application_for_host(hostname) or {})
