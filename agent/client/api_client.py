import hashlib
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests


logger = logging.getLogger("asset_sentinel.agent_api_client")

DEFAULT_API_URL = "http://127.0.0.1:5000"
DEFAULT_DEVELOPMENT_AGENT_TOKEN = "asset-sentinel-development-agent-token"
DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("ASSET_SENTINEL_AGENT_API_TIMEOUT_SECONDS", "2"))
DEFAULT_RETRIES = int(os.environ.get("ASSET_SENTINEL_AGENT_API_RETRIES", "1"))
ACTIVITY_USAGE_SYNC_SECONDS = int(os.environ.get("ASSET_SENTINEL_ACTIVITY_USAGE_SYNC_SECONDS", "15"))


def _api_url() -> str:
    return (os.environ.get("ASSET_SENTINEL_API_URL") or os.environ.get("API_URL") or DEFAULT_API_URL).rstrip("/")


def _agent_token() -> str:
    return os.environ.get("AGENT_TOKEN") or os.environ.get("ASSET_SENTINEL_AGENT_TOKEN") or DEFAULT_DEVELOPMENT_AGENT_TOKEN


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


def send_activity_sample(payload: Dict[str, Any]) -> Dict[str, Any]:
    return client().post("/api/agent/activity-sample", payload)


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
