import argparse
import atexit
import json
import logging
import os
import signal
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from active_application_monitor import POLL_INTERVAL_SECONDS, _record_signature, collect_active_application_record
from collect_hardware import collect_foreground_diagnostics, collect_hardware
from database import database_host_for_display, init_db
from monitoring_agent import TelemetrySpool
from service_logging import LOG_DIR, configure_logging
from storage import append_active_application, get_latest_active_application_for_host, resolve_device_uid, upsert_asset


logger = logging.getLogger("asset_sentinel.active_application_user_agent")
NO_FOREGROUND_LOG_INTERVAL_SECONDS = 30
SPOOL_RETRY_INTERVAL_SECONDS = 15
STATUS_PATH = LOG_DIR / "active_application_user_agent_status.json"
PID_PATH = LOG_DIR / "active_application_user_agent.pid"
STOP_PATH = LOG_DIR / "active_application_user_agent.stop"


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _acquire_single_instance() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if PID_PATH.exists():
        try:
            existing_pid = int(PID_PATH.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            existing_pid = 0
        if _pid_is_running(existing_pid):
            raise SystemExit(f"Active application user agent is already running as PID {existing_pid}.")
        PID_PATH.unlink(missing_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    STOP_PATH.unlink(missing_ok=True)

    def cleanup() -> None:
        try:
            if PID_PATH.exists() and PID_PATH.read_text(encoding="utf-8").strip() == str(os.getpid()):
                PID_PATH.unlink()
        except Exception:
            pass

    atexit.register(cleanup)


class ActiveApplicationUserAgent:
    def __init__(self, stop_event: Optional[threading.Event] = None) -> None:
        self.stop_event = stop_event or threading.Event()
        self.spool = TelemetrySpool(LOG_DIR / "active_application_spool.jsonl")
        self.last_signature_by_host: Dict[str, tuple] = {}
        self.last_no_foreground_log_at = 0.0
        self.last_spool_flush_at = 0.0

    def start(self) -> None:
        logger.info("Active application user-session agent starting.")
        logger.info("Database host: %s", database_host_for_display())
        logger.info("Foreground diagnostics at startup: %s", collect_foreground_diagnostics())
        init_db()
        try:
            hardware = collect_hardware()
            device_uid = resolve_device_uid(hardware)
            logger.info("Telemetry before insert: type=registration hostname=%s device_uid=%s", hardware.get("hostname"), device_uid)
            upsert_asset(hardware)
            logger.info("Telemetry after insert: type=registration hostname=%s device_uid=%s", hardware.get("hostname"), device_uid)
        except Exception as exc:
            logger.exception("Active application user-session registration failed; monitor will continue: %s", exc)
        self._seed_last_signature()
        self._write_status("started")
        logger.info("Active application user-session agent started.")

    def run_forever(self) -> None:
        self.start()
        while not self.stop_event.is_set():
            if STOP_PATH.exists():
                logger.info("Stop file detected, stopping active application user-session agent.")
                self.stop_event.set()
                break
            try:
                self._tick()
            except Exception as exc:
                logger.exception("Active application user-session tick failed and will continue: %s", exc)
            self.stop_event.wait(POLL_INTERVAL_SECONDS)
        self._write_status("stopped")
        logger.info("Active application user-session agent stopped.")

    def _seed_last_signature(self) -> None:
        hostname = socket.gethostname()
        latest = get_latest_active_application_for_host(hostname)
        if latest:
            self.last_signature_by_host[hostname] = _record_signature(latest)
            logger.info(
                "Seeded latest active application signature: hostname=%s application=%s timestamp=%s",
                hostname,
                latest.get("application") or latest.get("application_name"),
                latest.get("timestamp"),
            )

    def _tick(self) -> None:
        self._flush_spool_periodically()
        record = collect_active_application_record()
        if not record:
            self._write_status("running", foreground_visible=False)
            self._log_no_foreground_window()
            return

        hostname = record.get("hostname") or socket.gethostname()
        signature = _record_signature(record)
        if self.last_signature_by_host.get(hostname) == signature:
            self._write_status("running", record=record, foreground_visible=True, inserted=False)
            return

        logger.info(
            "Telemetry before insert: type=active_application hostname=%s application=%s window=%s",
            hostname,
            record.get("application_name"),
            record.get("window_title"),
        )
        logger.info(
            "Foreground application changed: hostname=%s application=%s window=%s",
            hostname,
            record.get("application_name"),
            record.get("window_title"),
        )
        try:
            append_active_application(record)
            self.last_signature_by_host[hostname] = signature
            logger.info("Telemetry after insert: type=active_application hostname=%s application=%s", hostname, record.get("application_name"))
            self._write_status("running", record=record, foreground_visible=True, inserted=True)
        except Exception as exc:
            logger.exception("Application event insert failed, spooling: %s", exc)
            self.spool.append("active_application", record, str(exc))
            self._write_status("spooled", record=record, foreground_visible=True, inserted=False, error=str(exc))

    def _flush_spool_periodically(self) -> None:
        now = time.time()
        if now - self.last_spool_flush_at < SPOOL_RETRY_INTERVAL_SECONDS:
            return
        self.last_spool_flush_at = now
        entries = self.spool.read_all()
        if not entries:
            return

        remaining = []
        uploaded = 0
        for entry in entries:
            try:
                if entry.get("event_type") != "active_application":
                    remaining.append(entry)
                    continue
                append_active_application(entry.get("payload") or {})
                uploaded += 1
            except Exception as exc:
                entry["last_error"] = str(exc)
                entry["last_attempt_at"] = datetime.now(timezone.utc).isoformat()
                remaining.append(entry)
        self.spool.replace_all(remaining)
        if uploaded:
            logger.info("Active application spool flushed: uploaded=%s remaining=%s", uploaded, len(remaining))

    def _log_no_foreground_window(self) -> None:
        now = time.time()
        if now - self.last_no_foreground_log_at < NO_FOREGROUND_LOG_INTERVAL_SECONDS:
            return
        self.last_no_foreground_log_at = now
        logger.warning(
            "No foreground window visible to this user-session agent. "
            "No active application event inserted because only real foreground data is accepted. "
            "diagnostics=%s",
            collect_foreground_diagnostics(),
        )

    def _write_status(
        self,
        state: str,
        record: Optional[Dict[str, Any]] = None,
        foreground_visible: Optional[bool] = None,
        inserted: Optional[bool] = None,
        error: Optional[str] = None,
    ) -> None:
        status = {
            "state": state,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "username": os.environ.get("USERNAME") or os.environ.get("USER") or os.environ.get("LOGNAME"),
            "session_id": os.environ.get("SESSIONNAME"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "foreground_visible": foreground_visible,
            "inserted": inserted,
            "application": (record or {}).get("application_name") or (record or {}).get("application"),
            "window_title": (record or {}).get("window_title"),
            "timestamp": (record or {}).get("timestamp"),
            "database_host": database_host_for_display(),
            "foreground_diagnostics": collect_foreground_diagnostics(),
            "error": error,
        }
        STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Asset Sentinel active application user-session agent.")
    parser.add_argument("--console", action="store_true", help="Log to stdout in addition to logs/agent.log.")
    args = parser.parse_args()

    configure_logging("agent", console=args.console)
    _acquire_single_instance()
    stop_event = threading.Event()

    def request_stop(signum, _frame):
        logger.info("Signal received, stopping active application user-session agent: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    ActiveApplicationUserAgent(stop_event=stop_event).run_forever()


if __name__ == "__main__":
    main()
