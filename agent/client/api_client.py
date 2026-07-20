import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests


logger = logging.getLogger("asset_sentinel.agent_api_client")

ROOT_DIR = Path(__file__).resolve().parents[2]
_ENV_LOADED = False


def load_agent_env(force: bool = False) -> None:
    """Load agent .env values without importing backend database settings."""
    global _ENV_LOADED
    if _ENV_LOADED and not force:
        return
    _ENV_LOADED = True

    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8-sig") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and (force or not os.environ.get(key)):
                os.environ[key] = value


load_agent_env()

DEFAULT_API_URL = "http://127.0.0.1:5000"
DEFAULT_DEVELOPMENT_AGENT_TOKEN = "asset-sentinel-development-agent-token"
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("ASSET_SENTINEL_AGENT_API_TIMEOUT_SECONDS", "10"))
DEFAULT_RETRIES = int(os.environ.get("ASSET_SENTINEL_AGENT_API_RETRIES", "2"))
ACTIVITY_USAGE_SYNC_SECONDS = int(os.environ.get("ASSET_SENTINEL_ACTIVITY_USAGE_SYNC_SECONDS", "15"))


def _api_url() -> str:
    return (os.environ.get("ASSET_SENTINEL_API_URL") or os.environ.get("API_URL") or DEFAULT_API_URL).rstrip("/")


def _agent_token() -> str:
    return os.environ.get("ASSET_SENTINEL_AGENT_TOKEN") or os.environ.get("AGENT_TOKEN") or DEFAULT_DEVELOPMENT_AGENT_TOKEN


def resolve_device_uid(record: Dict[str, Any]) -> str:
    for key in ("device_uid", "uuid", "bios_serial", "baseboard_serial", "mac_address"):
        value = record.get(key)
        if value:
            return str(value)
    hostname = record.get("hostname") or "Unknown"
    return hashlib.sha256(str(hostname).encode("utf-8")).hexdigest()[:32]


class AgentApiClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None) -> None:
        self.base_url = (base_url or _api_url()).rstrip("/")
        self.token = token if token is not None else _agent_token()
        self.timeout = DEFAULT_TIMEOUT_SECONDS
        self.retries = max(0, DEFAULT_RETRIES)
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.request(method, url, headers=self._headers(), timeout=self.timeout, **kwargs)
                response.raise_for_status()
                if not response.content:
                    return {}
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                time.sleep(min(0.25 * (attempt + 1), 1.0))
        raise RuntimeError(f"Agent API request failed: {method} {url}: {last_error}")

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, payload: Dict[str, Any]) -> Any:
        return self._request("POST", path, json=payload)


_client: Optional[AgentApiClient] = None
_last_activity_sample_by_host: Dict[str, Dict[str, Any]] = {}
_activity_usage_buffer: Dict[tuple, Dict[str, Any]] = {}
_last_activity_flush_at = time.monotonic()


def client() -> AgentApiClient:
    global _client
    if _client is None:
        _client = AgentApiClient()
    return _client


def send_register(payload: Dict[str, Any]) -> Dict[str, Any]:
    return client().post("/api/agent/register", payload)


def send_heartbeat(
    hostname: str,
    cpu_usage_percent: Any = None,
    ram_usage_percent: Any = None,
    current_active_application: Optional[Dict[str, Any]] = None,
    device_uid: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "hostname": hostname,
        "device_uid": device_uid or (current_active_application or {}).get("device_uid"),
        "cpu_usage_percent": cpu_usage_percent,
        "ram_usage_percent": ram_usage_percent,
        "current_active_application": current_active_application,
    }
    return client().post("/api/agent/heartbeat", payload)


def send_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    return client().post("/api/agent/session", payload)


def send_application(payload: Dict[str, Any], record_sample: bool = True) -> Dict[str, Any]:
    if record_sample:
        return client().post("/api/agent/application", payload)
    return client().post("/api/agent/application-event", payload)


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _activity_state(record: Dict[str, Any]) -> str:
    if record.get("windows_locked"):
        return "LOCKED"
    if record.get("is_user_idle"):
        return "IDLE"
    return "ACTIVE"


def _buffer_activity_interval(previous: Dict[str, Any], current: Dict[str, Any]) -> None:
    start = _parse_timestamp(previous.get("timestamp"))
    end = _parse_timestamp(current.get("timestamp"))
    seconds = max(0, int((end - start).total_seconds()))
    if seconds <= 0:
        return
    hostname = previous.get("hostname") or current.get("hostname") or "Unknown"
    username = previous.get("username") or current.get("username") or "Unknown"
    app_name = previous.get("application_name") or previous.get("application") or "Unknown"
    window_title = previous.get("window_title") or "Unknown"
    state = _activity_state(previous)
    key = (hostname, username, app_name, window_title, state, start.date().isoformat())
    buffered = _activity_usage_buffer.setdefault(
        key,
        {
            "hostname": hostname,
            "username": username,
            "application_name": app_name,
            "window_title": window_title,
            "process_path": previous.get("process_path") or previous.get("active_process_path") or previous.get("executable_name"),
            "state": state,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "duration_seconds": 0,
        },
    )
    buffered["duration_seconds"] = int(buffered.get("duration_seconds") or 0) + seconds
    buffered["end_time"] = end.isoformat()


def flush_activity_usage(force: bool = False) -> Dict[str, Any]:
    global _last_activity_flush_at
    now = time.monotonic()
    if not force and now - _last_activity_flush_at < ACTIVITY_USAGE_SYNC_SECONDS:
        return {"ok": True, "flushed": 0, "buffered": len(_activity_usage_buffer)}
    if not _activity_usage_buffer:
        _last_activity_flush_at = now
        return {"ok": True, "flushed": 0, "buffered": 0}
    pending_items = list(_activity_usage_buffer.items())
    records = [dict(record) for _, record in pending_items]
    try:
        response = client().post("/api/agent/activity-usage", {"records": records})
    except Exception:
        _last_activity_flush_at = now
        raise
    for key, _ in pending_items:
        _activity_usage_buffer.pop(key, None)
    _last_activity_flush_at = now
    return response


def send_activity_sample(payload: Dict[str, Any]) -> Dict[str, Any]:
    hostname = payload.get("hostname") or "Unknown"
    previous = _last_activity_sample_by_host.get(hostname)
    if previous:
        _buffer_activity_interval(previous, payload)
    _last_activity_sample_by_host[hostname] = dict(payload)
    return flush_activity_usage()


def send_alert(alert_type: str, hostname: str, severity: str, details: Dict[str, Any], timestamp: Any = None) -> Dict[str, Any]:
    return client().post(
        "/api/agent/alert",
        {
            "alert_type": alert_type,
            "hostname": hostname,
            "severity": severity,
            "details": details,
            "timestamp": timestamp,
        },
    )


def has_session_event_signature(hostname: str, windows_event_record_id: Optional[str]) -> bool:
    if not windows_event_record_id:
        return False
    response = client().get(
        "/api/agent/session/exists",
        {"hostname": hostname, "windows_event_record_id": windows_event_record_id},
    )
    return bool(response.get("exists"))


def activate_session_event(hostname: str, windows_event_record_id: Optional[str], last_seen: Optional[str] = None) -> bool:
    response = client().post(
        "/api/agent/session/activate",
        {
            "hostname": hostname,
            "windows_event_record_id": windows_event_record_id,
            "last_seen": last_seen,
        },
    )
    return bool(response.get("updated"))


def touch_active_session(hostname: str, username: Optional[str], session_id: Optional[str]) -> None:
    client().post("/api/agent/session/touch", {"hostname": hostname, "username": username, "session_id": session_id})


def list_active_applications_history() -> List[Dict[str, Any]]:
    response = client().get("/api/agent/applications/history")
    return response if isinstance(response, list) else []


def get_latest_active_application_for_host(hostname: str) -> Optional[Dict[str, Any]]:
    response = client().get(f"/api/agent/applications/latest/{hostname}")
    return response if isinstance(response, dict) and response else None


def list_sessions() -> List[Dict[str, Any]]:
    response = client().get("/api/agent/sessions")
    return response if isinstance(response, list) else []


def replace_sessions(sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return client().post("/api/agent/sessions/replace", {"sessions": sessions})


def list_alerts() -> List[Dict[str, Any]]:
    response = client().get("/api/agent/alerts")
    return response if isinstance(response, list) else []


def list_assets() -> List[Dict[str, Any]]:
    response = client().get("/api/agent/assets")
    return response if isinstance(response, list) else []


def record_hardware_change(
    hostname: str,
    change_type: str,
    severity: str,
    previous_value: Dict[str, Any],
    current_value: Dict[str, Any],
    difference: Dict[str, Any],
    detected_at: Any = None,
) -> Dict[str, Any]:
    return client().post(
        "/api/agent/hardware-change",
        {
            "hostname": hostname,
            "change_type": change_type,
            "severity": severity,
            "previous_value": previous_value,
            "current_value": current_value,
            "difference": difference,
            "detected_at": detected_at,
        },
    )
