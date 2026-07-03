import logging
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from collect_hardware import collect_hardware
from database import verify_database_health
from monitoring_agent import AssetSentinelAgent
from service_logging import LOG_DIR
from storage import get_device_health, resolve_device_uid


logger = logging.getLogger("asset_sentinel.startup_health")

_agent_lock = threading.Lock()
_agent: Optional[AssetSentinelAgent] = None
_agent_started = False
_startup_report: Dict[str, Any] = {}


def _ok(value: bool) -> str:
    return "OK" if value else "FAIL"


def start_local_agent_supervisor() -> AssetSentinelAgent:
    global _agent, _agent_started
    with _agent_lock:
        if _agent is None:
            _agent = AssetSentinelAgent()
        if not _agent_started:
            _agent.start()
            _agent_started = True
        return _agent


def get_local_agent() -> Optional[AssetSentinelAgent]:
    return _agent


def run_startup_checks(start_agent: bool = True) -> Dict[str, Any]:
    global _startup_report
    report: Dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "database": {"status": "FAIL"},
        "registration": {"status": "FAIL"},
        "heartbeat": {"status": "FAIL"},
        "login_tracker": {"status": "FAIL"},
        "active_application": {"status": "FAIL"},
        "windows_hooks": {"status": "FAIL"},
        "telemetry_pipeline": {"status": "FAIL"},
    }

    database = verify_database_health()
    report["database"] = {
        "status": _ok(bool(database.get("connected") and database.get("schema_ok") and database.get("required_tables_ok"))),
        **database,
    }

    try:
        hardware = collect_hardware()
        report["registration"] = {
            "status": _ok(bool(hardware.get("hostname"))),
            "hostname": hardware.get("hostname"),
            "device_uid": resolve_device_uid(hardware),
            "collection_method": hardware.get("collection_method"),
            "collection_errors": hardware.get("collection_errors") or [],
        }
    except Exception as exc:
        report["registration"] = {"status": "FAIL", "error": str(exc)}

    agent = None
    if start_agent and report["database"]["status"] == "OK":
        try:
            agent = start_local_agent_supervisor()
        except Exception as exc:
            logger.exception("Local telemetry supervisor failed to start: %s", exc)
            report["telemetry_pipeline"] = {"status": "FAIL", "error": str(exc)}

    if agent:
        snapshot = agent.health_snapshot()
        threads = snapshot.get("threads") or {}
        health = snapshot.get("health") or {}
        report["heartbeat"] = _worker_report("heartbeat", threads, health)
        report["login_tracker"] = _worker_report("login-activity", threads, health)
        report["active_application"] = _worker_report("active-application", threads, health)
        report["windows_hooks"] = {
            "status": report["login_tracker"]["status"],
            "session_hook_active": report["login_tracker"]["status"] == "OK",
            "event_log_subscription_active": report["login_tracker"]["status"] == "OK",
            "reason": report["login_tracker"].get("last_error"),
        }
        report["telemetry_pipeline"] = {
            "status": _ok(
                report["database"]["status"] == "OK"
                and report["registration"]["status"] == "OK"
                and report["heartbeat"]["status"] == "OK"
                and report["login_tracker"]["status"] == "OK"
                and report["active_application"]["status"] == "OK"
            ),
            "agent": snapshot,
        }

    _startup_report = report
    print_startup_health_report(report)
    return report


def _worker_report(name: str, threads: Dict[str, Any], health: Dict[str, Any]) -> Dict[str, Any]:
    thread = threads.get(name) or {}
    worker = health.get(name) or {}
    return {
        "status": _ok(bool(thread.get("alive"))),
        "thread_alive": bool(thread.get("alive")),
        "thread_ident": thread.get("ident"),
        "last_success_at": worker.get("last_success_at"),
        "last_error": worker.get("last_error"),
        "updated_at": worker.get("updated_at"),
    }


def startup_health_response() -> Dict[str, Any]:
    report = _startup_report or run_startup_checks(start_agent=False)
    return {
        "database": report.get("database", {}).get("status", "FAIL"),
        "heartbeat": report.get("heartbeat", {}).get("status", "FAIL"),
        "login_tracker": report.get("login_tracker", {}).get("status", "FAIL"),
        "active_application": report.get("active_application", {}).get("status", "FAIL"),
        "registration": report.get("registration", {}).get("status", "FAIL"),
        "windows_hooks": report.get("windows_hooks", {}).get("status", "FAIL"),
        "telemetry_pipeline": report.get("telemetry_pipeline", {}).get("status", "FAIL"),
        "details": report,
    }


def device_health_response(identifier: str) -> Optional[Dict[str, Any]]:
    db_health = get_device_health(identifier)
    if not db_health:
        return None
    agent = get_local_agent()
    snapshot = agent.health_snapshot() if agent else {}
    threads = snapshot.get("threads") or {}
    health = snapshot.get("health") or {}
    db_health.update({
        "heartbeat_thread": _worker_report("heartbeat", threads, health),
        "login_tracker_status": _worker_report("login-activity", threads, health),
        "active_application_status": _worker_report("active-application", threads, health),
        "latest_errors": _latest_log_errors(),
    })
    return db_health


def _latest_log_errors(limit: int = 20) -> list[str]:
    candidates = [LOG_DIR / "agent.log", LOG_DIR / "service.log", LOG_DIR / "app.log"]
    errors: list[str] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
        except Exception:
            continue
        for line in lines:
            if "ERROR" in line or "WARNING" in line or "Traceback" in line:
                errors.append(f"{Path(path).name}: {line}")
    return errors[-limit:]


def print_startup_health_report(report: Dict[str, Any]) -> None:
    labels = [
        ("database", "Database Connected"),
        ("registration", "Device Registered"),
        ("heartbeat", "Heartbeat Running"),
        ("login_tracker", "Login Tracker Running"),
        ("active_application", "Active Application Running"),
        ("windows_hooks", "Windows Session Hook Active"),
        ("windows_hooks", "Event Log Subscription Active"),
    ]
    for key, label in labels:
        item = report.get(key) or {}
        ok = item.get("status") == "OK"
        reason = item.get("error") or item.get("last_error") or item.get("reason")
        prefix = "[OK]" if ok else "[FAIL]"
        print(f"{prefix} {label}" + (f": {reason}" if reason else ""))
