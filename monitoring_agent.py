import argparse
import json
import logging
import os
import signal
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from active_application_monitor import (
    POLL_INTERVAL_SECONDS,
    _record_signature,
    _record_unlock_fallback_if_needed,
    collect_active_application_record,
)
from collect_hardware import collect_hardware
from config import Config
from database import database_host_for_display, init_db
from login_tracker import detect_login
from service_logging import LOG_DIR, configure_logging, ensure_log_dir
from storage import (
    append_active_application,
    append_alert,
    append_session,
    normalize_active_application_timestamps,
    resolve_device_uid,
    update_asset_heartbeat,
    upsert_asset,
)
from telemetry_bootstrap import _find_existing_asset, _record_change_if_needed


logger = logging.getLogger("asset_sentinel.agent")

LOGIN_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_LOGIN_POLL_SECONDS", "5"))
HARDWARE_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_HARDWARE_POLL_SECONDS", "900"))
SPOOL_RETRY_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_SPOOL_RETRY_SECONDS", "30"))
HEARTBEAT_LOG_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_HEARTBEAT_LOG_SECONDS", "60"))


class TelemetrySpool:
    def __init__(self, path: Optional[Path] = None) -> None:
        ensure_log_dir()
        self.path = path or (LOG_DIR / "telemetry_spool.jsonl")
        self._lock = threading.Lock()

    def append(self, event_type: str, payload: Dict[str, Any], reason: str = "") -> None:
        entry = {
            "event_type": event_type,
            "payload": payload,
            "reason": reason,
            "spooled_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, default=str) + "\n")
        logger.warning("Telemetry spooled: type=%s reason=%s", event_type, reason)

    def read_all(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with self._lock:
            entries: List[Dict[str, Any]] = []
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.error("Discarding malformed telemetry spool line: %s", line[:200])
            return entries

    def replace_all(self, entries: Iterable[Dict[str, Any]]) -> None:
        entries = list(entries)
        with self._lock:
            if not entries:
                if self.path.exists():
                    self.path.unlink()
                return
            with self.path.open("w", encoding="utf-8") as handle:
                for entry in entries:
                    handle.write(json.dumps(entry, default=str) + "\n")


class AssetSentinelAgent:
    def __init__(self, stop_event: Optional[threading.Event] = None, spool: Optional[TelemetrySpool] = None) -> None:
        self.stop_event = stop_event or threading.Event()
        self.spool = spool or TelemetrySpool()
        self._threads: List[threading.Thread] = []
        self._last_active_signature_by_host: Dict[str, tuple] = {}
        self._last_heartbeat_log_at = 0.0

    def start(self) -> None:
        logger.info("Asset Sentinel monitoring agent starting.")
        logger.info("Database URL configured from ASSET_SENTINEL_DATABASE_URL: %s", bool(Config.SQLALCHEMY_DATABASE_URL))
        logger.info("Database host: %s", database_host_for_display())
        init_db()
        corrected = normalize_active_application_timestamps()
        if corrected:
            logger.info("Corrected %s future active application timestamps.", corrected)

        self._run_hardware_cycle(spool_on_failure=True)
        self._start_thread("spool-retry", self._spool_retry_loop)
        self._start_thread("hardware-inventory", self._hardware_loop)
        self._start_thread("login-activity", self._login_loop)
        self._start_thread("active-application", self._active_application_loop)
        logger.info("Asset Sentinel monitoring agent started.")

    def run_forever(self) -> None:
        self.start()
        try:
            while not self.stop_event.wait(1):
                pass
        finally:
            self.stop()

    def stop(self, timeout: float = 15.0) -> None:
        logger.info("Asset Sentinel monitoring agent shutdown requested.")
        self.stop_event.set()
        deadline = time.time() + timeout
        for thread in self._threads:
            remaining = max(0.1, deadline - time.time())
            thread.join(timeout=remaining)
        logger.info("Asset Sentinel monitoring agent stopped.")

    def _start_thread(self, name: str, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=lambda: self._thread_main(name, target), name=f"asset-sentinel-{name}", daemon=True)
        self._threads.append(thread)
        thread.start()

    def _thread_main(self, name: str, target: Callable[[], None]) -> None:
        pythoncom = None
        try:
            try:
                import pythoncom as pythoncom_module
                pythoncom = pythoncom_module
                pythoncom.CoInitialize()
                logger.debug("COM initialized for thread %s", name)
            except Exception as exc:
                logger.debug("COM initialization skipped for thread %s: %s", name, exc)
            target()
        except Exception as exc:
            logger.exception("Agent thread crashed: name=%s error=%s", name, exc)
        finally:
            if pythoncom is not None:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass

    def _wait(self, seconds: int) -> bool:
        return self.stop_event.wait(seconds)

    def _spool_retry_loop(self) -> None:
        while not self.stop_event.is_set():
            self.flush_spool()
            self._wait(SPOOL_RETRY_INTERVAL_SECONDS)

    def _hardware_loop(self) -> None:
        self._wait(HARDWARE_POLL_INTERVAL_SECONDS)
        while not self.stop_event.is_set():
            self._run_hardware_cycle(spool_on_failure=True)
            self._wait(HARDWARE_POLL_INTERVAL_SECONDS)

    def _login_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                record = detect_login()
                if record:
                    logger.info(
                        "Login activity processed: user=%s host=%s source=%s",
                        record.get("username"),
                        record.get("hostname"),
                        record.get("login_source"),
                    )
            except Exception as exc:
                logger.exception("Login activity polling failed: %s", exc)
            self._wait(LOGIN_POLL_INTERVAL_SECONDS)

    def _active_application_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                record = collect_active_application_record()
                cpu_usage, ram_usage = self._usage_snapshot()
                update_asset_heartbeat(socket.gethostname(), cpu_usage, ram_usage, record)
                self._log_heartbeat(cpu_usage, ram_usage, record)
                _record_unlock_fallback_if_needed(record)
                if record and self._is_new_active_application(record):
                    self._upload_or_spool("active_application", record)
            except Exception as exc:
                logger.exception("Active application polling failed: %s", exc)
            self._wait(POLL_INTERVAL_SECONDS)

    def _run_hardware_cycle(self, spool_on_failure: bool) -> None:
        try:
            hardware = collect_hardware()
            self._upload_hardware(hardware)
            logger.info(
                "Hardware inventory uploaded: hostname=%s method=%s errors=%s",
                hardware.get("hostname"),
                hardware.get("collection_method"),
                len(hardware.get("collection_errors") or []),
            )
        except Exception as exc:
            logger.exception("Hardware inventory upload failed: %s", exc)
            if spool_on_failure:
                try:
                    fallback_hardware = collect_hardware()
                    self.spool.append("hardware_inventory", fallback_hardware, str(exc))
                except Exception as collect_exc:
                    logger.exception("Hardware inventory collection failed before spooling: %s", collect_exc)

    def _upload_or_spool(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            self._upload_event(event_type, payload)
            logger.info("Telemetry uploaded: type=%s", event_type)
        except Exception as exc:
            logger.exception("Telemetry upload failed: type=%s error=%s", event_type, exc)
            self.spool.append(event_type, payload, str(exc))

    def _upload_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "active_application":
            append_active_application(payload)
            return
        if event_type == "hardware_inventory":
            self._upload_hardware(payload)
            return
        if event_type == "session_record":
            append_session(payload)
            if payload.get("event_type"):
                append_alert(
                    payload.get("event_type"),
                    payload.get("hostname") or "Unknown",
                    "LOW" if payload.get("event_type") == "LOGOUT" else "MEDIUM",
                    {
                        "username": payload.get("username"),
                        "ip_address": payload.get("ip_address"),
                        "session_id": payload.get("session_id"),
                        "login_timestamp": payload.get("login_timestamp"),
                        "logout_timestamp": payload.get("logout_timestamp"),
                    },
                    datetime.now(timezone.utc).isoformat(),
                )
            return
        raise ValueError(f"Unknown telemetry event type: {event_type}")

    def _upload_hardware(self, hardware: Dict[str, Any]) -> None:
        existing = _find_existing_asset(resolve_device_uid(hardware), hardware.get("hostname"))
        _record_change_if_needed(existing, hardware)
        upsert_asset(hardware)

    def flush_spool(self) -> None:
        entries = self.spool.read_all()
        if not entries:
            return

        remaining: List[Dict[str, Any]] = []
        uploaded = 0
        for entry in entries:
            try:
                self._upload_event(entry.get("event_type"), entry.get("payload") or {})
                uploaded += 1
            except Exception as exc:
                entry["last_error"] = str(exc)
                entry["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
                remaining.append(entry)
        self.spool.replace_all(remaining)
        if uploaded:
            logger.info("Telemetry spool flushed: uploaded=%s remaining=%s", uploaded, len(remaining))
        elif remaining:
            logger.warning("Telemetry spool retry failed: remaining=%s", len(remaining))

    def _is_new_active_application(self, record: Dict[str, Any]) -> bool:
        hostname = record.get("hostname") or socket.gethostname()
        signature = _record_signature(record)
        if self._last_active_signature_by_host.get(hostname) == signature:
            return False
        self._last_active_signature_by_host[hostname] = signature
        return True

    def _usage_snapshot(self) -> tuple:
        try:
            import psutil
            return round(float(psutil.cpu_percent(interval=None)), 2), round(float(psutil.virtual_memory().percent), 2)
        except Exception:
            return None, None

    def _log_heartbeat(self, cpu_usage: Any, ram_usage: Any, record: Optional[Dict[str, Any]]) -> None:
        now = time.time()
        if now - self._last_heartbeat_log_at < HEARTBEAT_LOG_INTERVAL_SECONDS:
            return
        self._last_heartbeat_log_at = now
        logger.info(
            "Heartbeat uploaded: hostname=%s cpu=%s ram=%s active_app=%s",
            socket.gethostname(),
            cpu_usage,
            ram_usage,
            (record or {}).get("application_name"),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Asset Sentinel monitoring agent.")
    parser.add_argument("--console", action="store_true", help="Log to stdout in addition to logs/agent.log.")
    args = parser.parse_args()

    configure_logging("agent", console=args.console)
    stop_event = threading.Event()

    def request_stop(signum, _frame):
        logger.info("Signal received, stopping agent: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    AssetSentinelAgent(stop_event=stop_event).run_forever()


if __name__ == "__main__":
    main()
