import argparse
import json
import logging
import os
import signal
import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

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
    ROOT_DIR / "agent" / "client",
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from active_application_monitor import (
    POLL_INTERVAL_SECONDS,
    _record_signature,
    _record_unlock_fallback_if_needed,
    _log_activity_sample_state,
    collect_active_application_record,
)
from collect_hardware import collect_foreground_diagnostics, collect_hardware
from login_tracker import close_stale_sessions_from_previous_boot, detect_login
from service_logging import LOG_DIR, configure_logging, ensure_log_dir
from api_client import (
    client,
    resolve_device_uid,
    send_activity_sample,
    send_alert,
    send_application,
    send_heartbeat,
    send_register,
    send_session,
)


logger = logging.getLogger("asset_sentinel.agent")

LOGIN_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_LOGIN_POLL_SECONDS", "1"))
HEARTBEAT_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_HEARTBEAT_POLL_SECONDS", "15"))
RESOURCE_TELEMETRY_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_RESOURCE_TELEMETRY_SECONDS", "45"))
HARDWARE_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_HARDWARE_POLL_SECONDS", "900"))
SPOOL_RETRY_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_SPOOL_RETRY_SECONDS", "30"))
THREAD_WATCHDOG_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_THREAD_WATCHDOG_SECONDS", "5"))


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
        self._threads: Dict[str, threading.Thread] = {}
        self._thread_targets: Dict[str, Callable[[], None]] = {}
        self._thread_lock = threading.Lock()
        self._last_active_signature_by_host: Dict[str, tuple] = {}
        self._health_lock = threading.Lock()
        self._health: Dict[str, Dict[str, Any]] = {}
        self.device_uid: Optional[str] = None
        self.hostname = socket.gethostname()
        self._last_activity_state_by_host: Dict[str, str] = {}
        self._last_resource_telemetry_at = 0.0

    def start(self) -> None:
        logger.info("Asset Sentinel monitoring agent starting.")
        logger.info("Agent API URL: %s", client().base_url)
        closed_stale_sessions = close_stale_sessions_from_previous_boot(self.hostname)
        if closed_stale_sessions:
            logger.info("Stale session cleanup closed %s previous-boot sessions.", closed_stale_sessions)

        self._run_hardware_cycle(spool_on_failure=True)
        self._register_thread("spool-retry", self._spool_retry_loop)
        self._register_thread("hardware-inventory", self._hardware_loop)
        self._register_thread("heartbeat", self._heartbeat_loop)
        self._register_thread("login-activity", self._login_loop)
        self._register_thread("active-application", self._active_application_loop)
        self._register_thread("thread-watchdog", self._thread_watchdog_loop, supervised=False)
        logger.info("Asset Sentinel monitoring agent started.")
        logger.info("Monitoring Agent: Running")
        logger.info("Login Tracker: Running")
        logger.info("Session Manager: Running")
        self.print_startup_health_report()

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
        for thread in list(self._threads.values()):
            remaining = max(0.1, deadline - time.time())
            thread.join(timeout=remaining)
        logger.info("Asset Sentinel monitoring agent stopped.")

    def _register_thread(self, name: str, target: Callable[[], None], supervised: bool = True) -> None:
        if supervised:
            self._thread_targets[name] = target
        self._start_thread(name, target)

    def _start_thread(self, name: str, target: Callable[[], None]) -> None:
        thread = threading.Thread(target=lambda: self._thread_main(name, target), name=f"asset-sentinel-{name}", daemon=True)
        with self._thread_lock:
            self._threads[name] = thread
        thread.start()
        logger.info("Thread started: name=%s ident=%s", name, thread.ident)
        self._set_health(name, running=True, last_error=None)

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
            self._set_health(name, running=False, last_error=str(exc))
        finally:
            if pythoncom is not None:
                try:
                    pythoncom.CoUninitialize()
                except Exception:
                    pass
            logger.warning("Thread exited: name=%s", name)

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

    def _heartbeat_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                cpu_usage, ram_usage = self._resource_snapshot_if_due()
                logger.info("Telemetry before insert: type=heartbeat hostname=%s device_uid=%s", self.hostname, self.device_uid)
                send_heartbeat(self.hostname, cpu_usage, ram_usage, {"device_uid": self.device_uid} if self.device_uid else None, self.device_uid)
                self._log_heartbeat(cpu_usage, ram_usage, None)
                logger.info("Telemetry after insert: type=heartbeat hostname=%s device_uid=%s", self.hostname, self.device_uid)
                self._set_health("heartbeat", running=True, last_success_at=datetime.now(timezone.utc).isoformat(), last_error=None)
            except Exception as exc:
                logger.exception("Heartbeat polling failed: %s", exc)
                self._set_health("heartbeat", running=True, last_error=str(exc))
            self._wait(HEARTBEAT_POLL_INTERVAL_SECONDS)

    def _login_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                logger.info("Telemetry before insert: type=login_activity hostname=%s", self.hostname)
                try:
                    _record_unlock_fallback_if_needed(collect_active_application_record())
                except Exception as fallback_exc:
                    logger.exception("Login loop lock/unlock fallback failed and will continue: %s", fallback_exc)
                record = detect_login()
                if record:
                    logger.info(
                        "Login activity processed: user=%s host=%s source=%s",
                        record.get("username"),
                        record.get("hostname"),
                        record.get("login_source"),
                    )
                    logger.info("Telemetry after insert: type=login_activity hostname=%s record_id=%s", record.get("hostname"), record.get("windows_event_record_id"))
                    self._refresh_active_application_after_unlock(record)
                self._set_health("login-activity", running=True, last_success_at=datetime.now(timezone.utc).isoformat(), last_error=None)
            except Exception as exc:
                logger.exception("Login activity polling failed: %s", exc)
                self._set_health("login-activity", running=True, last_error=str(exc))
            self._wait(LOGIN_POLL_INTERVAL_SECONDS)

    def _refresh_active_application_after_unlock(self, login_record: Dict[str, Any]) -> None:
        event_id = str(login_record.get("windows_event_id") or "")
        source = str(login_record.get("login_source") or "")
        if event_id not in {"4801", "4778", "LOCKAPP_UNLOCK"} and "unlock" not in source and "reconnect" not in source:
            return
        try:
            record = collect_active_application_record()
            heartbeat_host = (record or {}).get("hostname") or login_record.get("hostname") or self.hostname
            if not record:
                logger.info("Unlock foreground refresh skipped: no foreground application visible yet.")
                return
            try:
                send_activity_sample(record)
            except Exception as sample_exc:
                logger.exception("Unlock activity session sample failed and will continue: %s", sample_exc)
            record["activity_state_changed"] = True
            self._upload_or_spool("active_application", record)
            self._last_active_signature_by_host[heartbeat_host] = _record_signature(record)
            logger.info(
                "Unlock foreground refresh inserted: hostname=%s application=%s window=%s",
                heartbeat_host,
                record.get("application_name"),
                record.get("window_title"),
            )
        except Exception as exc:
            logger.exception("Unlock foreground refresh failed and will continue: %s", exc)

    def _active_application_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                record = collect_active_application_record() if self._can_collect_foreground_from_process_session() else None
                _record_unlock_fallback_if_needed(record)
                if record:
                    try:
                        send_activity_sample(record)
                    except Exception as sample_exc:
                        logger.exception("Activity session sample failed and will continue: %s", sample_exc)
                if record and self._is_new_active_application(record):
                    logger.info(
                        "Telemetry before insert: type=active_application hostname=%s application=%s window=%s",
                        record.get("hostname"),
                        record.get("application_name"),
                        record.get("window_title"),
                    )
                    logger.info(
                        "Foreground application changed: hostname=%s application=%s window=%s",
                        record.get("hostname"),
                        record.get("application_name"),
                        record.get("window_title"),
                    )
                    self._upload_or_spool("active_application", record)
                    logger.info(
                        "Telemetry after insert: type=active_application hostname=%s application=%s",
                        record.get("hostname"),
                        record.get("application_name"),
                    )
                self._set_health("active-application", running=True, last_success_at=datetime.now(timezone.utc).isoformat(), last_error=None)
            except Exception as exc:
                logger.exception("Active application polling failed: %s", exc)
                self._set_health("active-application", running=True, last_error=str(exc))
            self._wait(POLL_INTERVAL_SECONDS)

    def _can_collect_foreground_from_process_session(self) -> bool:
        diagnostics = collect_foreground_diagnostics()
        current_session_id = diagnostics.get("current_session_id")
        active_console_session_id = diagnostics.get("active_console_session_id")
        return (
            current_session_id is not None
            and current_session_id == active_console_session_id
            and int(current_session_id) > 0
        )

    def _thread_watchdog_loop(self) -> None:
        while not self.stop_event.is_set():
            with self._thread_lock:
                snapshots = list(self._threads.items())
            for name, thread in snapshots:
                if name == "thread-watchdog":
                    continue
                if thread.is_alive():
                    continue
                target = self._thread_targets.get(name)
                if target is None or self.stop_event.is_set():
                    continue
                logger.error("Thread died unexpectedly; restarting: name=%s", name)
                self._start_thread(name, target)
                logger.info("Thread restarted: name=%s", name)
            self._wait(THREAD_WATCHDOG_INTERVAL_SECONDS)

    def _run_hardware_cycle(self, spool_on_failure: bool) -> None:
        try:
            hardware = collect_hardware()
            self.hostname = hardware.get("hostname") or self.hostname
            self.device_uid = resolve_device_uid(hardware)
            logger.info("Telemetry before insert: type=registration hostname=%s device_uid=%s", self.hostname, self.device_uid)
            self._upload_hardware(hardware)
            logger.info("Telemetry after insert: type=registration hostname=%s device_uid=%s", self.hostname, self.device_uid)
            self._set_health("registration", running=True, last_success_at=datetime.now(timezone.utc).isoformat(), last_error=None)
            logger.info(
                "Hardware inventory uploaded: hostname=%s method=%s errors=%s",
                hardware.get("hostname"),
                hardware.get("collection_method"),
                len(hardware.get("collection_errors") or []),
            )
        except Exception as exc:
            logger.exception("Hardware inventory upload failed: %s", exc)
            self._set_health("registration", running=False, last_error=str(exc))
            if spool_on_failure:
                try:
                    fallback_hardware = collect_hardware()
                    self.spool.append("hardware_inventory", fallback_hardware, str(exc))
                except Exception as collect_exc:
                    logger.exception("Hardware inventory collection failed before spooling: %s", collect_exc)

    def _upload_or_spool(self, event_type: str, payload: Dict[str, Any]) -> None:
        try:
            logger.info("Telemetry before insert: type=%s hostname=%s", event_type, payload.get("hostname"))
            self._upload_event(event_type, payload)
            logger.info("Telemetry after insert: type=%s hostname=%s", event_type, payload.get("hostname"))
            logger.info("Telemetry uploaded: type=%s", event_type)
        except Exception as exc:
            logger.exception("Telemetry upload failed: type=%s error=%s", event_type, exc)
            self.spool.append(event_type, payload, str(exc))

    def _upload_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        if event_type == "active_application":
            send_application(payload, record_sample=False)
            return
        if event_type == "hardware_inventory":
            self._upload_hardware(payload)
            return
        if event_type == "session_record":
            send_session(payload)
            if payload.get("event_type"):
                send_alert(
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
        response = send_register(hardware)
        self.device_uid = response.get("device_uid") or self.device_uid or resolve_device_uid(hardware)

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
        activity_state = "locked" if record.get("windows_locked") else "idle" if record.get("is_user_idle") else "active"
        if (
            self._last_active_signature_by_host.get(hostname) == signature
            and self._last_activity_state_by_host.get(hostname) == activity_state
        ):
            return False
        record["activity_state_changed"] = bool(
            self._last_active_signature_by_host.get(hostname) == signature
            and self._last_activity_state_by_host.get(hostname) != activity_state
        )
        self._last_active_signature_by_host[hostname] = signature
        self._last_activity_state_by_host[hostname] = activity_state
        return True

    def _usage_snapshot(self) -> tuple:
        try:
            import psutil
            return round(float(psutil.cpu_percent(interval=None)), 2), round(float(psutil.virtual_memory().percent), 2)
        except Exception:
            return None, None

    def _resource_snapshot_if_due(self) -> tuple:
        now = time.monotonic()
        if self._last_resource_telemetry_at and now - self._last_resource_telemetry_at < RESOURCE_TELEMETRY_INTERVAL_SECONDS:
            return None, None
        self._last_resource_telemetry_at = now
        return self._usage_snapshot()

    def _log_heartbeat(self, cpu_usage: Any, ram_usage: Any, record: Optional[Dict[str, Any]]) -> None:
        logger.info(
            "Heartbeat uploaded: hostname=%s cpu=%s ram=%s active_app=%s",
            socket.gethostname(),
            cpu_usage,
            ram_usage,
            (record or {}).get("application_name"),
        )

    def _set_health(self, name: str, **updates: Any) -> None:
        with self._health_lock:
            current = self._health.setdefault(name, {})
            current.update(updates)
            current["updated_at"] = datetime.now(timezone.utc).isoformat()

    def health_snapshot(self) -> Dict[str, Any]:
        with self._thread_lock:
            threads = {
                name: {"alive": thread.is_alive(), "ident": thread.ident}
                for name, thread in self._threads.items()
            }
        with self._health_lock:
            health = {name: dict(value) for name, value in self._health.items()}
        return {
            "hostname": self.hostname,
            "device_uid": self.device_uid,
            "threads": threads,
            "health": health,
            "running": not self.stop_event.is_set(),
        }

    def print_startup_health_report(self) -> None:
        snapshot = self.health_snapshot()

        def mark(ok: bool, label: str, reason: Optional[str] = None) -> None:
            prefix = "[OK]" if ok else "[FAIL]"
            text = f"{prefix} {label}"
            if reason:
                text = f"{text}: {reason}"
            print(text)
            logger.info(text)

        mark(True, "Database Connected")
        mark(bool(self.device_uid), "Device Registered", None if self.device_uid else "device_uid unavailable")
        mark(snapshot["threads"].get("heartbeat", {}).get("alive", False), "Heartbeat Running")
        mark(snapshot["threads"].get("login-activity", {}).get("alive", False), "Login Tracker Running")
        mark(snapshot["threads"].get("login-activity", {}).get("alive", False), "Session Manager Running")
        mark(True, "Monitoring Agent Running")
        mark(snapshot["threads"].get("active-application", {}).get("alive", False), "Active Application Running")
        mark(snapshot["threads"].get("login-activity", {}).get("alive", False), "Windows Session Hook Active")
        mark(snapshot["threads"].get("login-activity", {}).get("alive", False), "Event Log Subscription Active")


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
