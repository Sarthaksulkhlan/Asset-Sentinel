import argparse
import atexit
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
from typing import Any, Dict, Optional

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
    activity_state_from_record,
    collect_active_application_record,
)
from collect_hardware import collect_foreground_diagnostics, collect_hardware
from monitoring_agent import TelemetrySpool
from service_logging import LOG_DIR, configure_logging
from api_client import (
    client,
    get_latest_active_application_for_host,
    resolve_device_uid,
    send_activity_sample,
    send_application,
    send_register,
)


logger = logging.getLogger("asset_sentinel.active_application_user_agent")
NO_FOREGROUND_LOG_INTERVAL_SECONDS = 30
SPOOL_RETRY_INTERVAL_SECONDS = 15
STARTUP_RETRY_INTERVAL_SECONDS = 15
TOP_LEVEL_RESTART_INTERVAL_SECONDS = 10
STATUS_PATH = LOG_DIR / "active_application_user_agent_status.json"
PID_PATH = LOG_DIR / "active_application_user_agent.pid"
STOP_PATH = LOG_DIR / "active_application_user_agent.stop"
LOCK_PATH = LOG_DIR / "active_application_user_agent.lock"
_LOCK_FILE = None


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
    global _LOCK_FILE

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import msvcrt

        _LOCK_FILE = LOCK_PATH.open("a+b")
        _LOCK_FILE.seek(0)
        _LOCK_FILE.write(b"0")
        _LOCK_FILE.flush()
        _LOCK_FILE.seek(0)
        msvcrt.locking(_LOCK_FILE.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        raise SystemExit("Active application user agent is already running; lock is held.") from exc
    except ImportError:
        _LOCK_FILE = None

    if PID_PATH.exists():
        try:
            existing_pid = int(PID_PATH.read_text(encoding="utf-8").strip() or "0")
        except ValueError:
            existing_pid = 0
        if existing_pid:
            logger.info("Replacing stale active application PID file. previous_pid=%s", existing_pid)
        PID_PATH.unlink(missing_ok=True)
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    STOP_PATH.unlink(missing_ok=True)

    def cleanup() -> None:
        global _LOCK_FILE
        try:
            if PID_PATH.exists() and PID_PATH.read_text(encoding="utf-8").strip() == str(os.getpid()):
                PID_PATH.unlink()
        except Exception:
            pass
        if _LOCK_FILE is not None:
            try:
                import msvcrt

                _LOCK_FILE.seek(0)
                msvcrt.locking(_LOCK_FILE.fileno(), msvcrt.LK_UNLCK, 1)
                _LOCK_FILE.close()
            except Exception:
                pass
            _LOCK_FILE = None
        logger.info("Active application user-session agent process shutdown cleanup completed.")

    atexit.register(cleanup)


class ActiveApplicationUserAgent:
    def __init__(self, stop_event: Optional[threading.Event] = None) -> None:
        self.stop_event = stop_event or threading.Event()
        self.spool = TelemetrySpool(LOG_DIR / "active_application_spool.jsonl")
        self.last_signature_by_host: Dict[str, tuple] = {}
        self.last_activity_state_by_host: Dict[str, str] = {}
        self.last_no_foreground_log_at = 0.0
        self.last_spool_flush_at = 0.0

    def start(self) -> bool:
        logger.info("Active application user-session agent starting.")
        logger.info("Agent API URL: %s", client().base_url)
        logger.info("Foreground diagnostics at startup: %s", collect_foreground_diagnostics())
        try:
            hardware = collect_hardware()
            device_uid = resolve_device_uid(hardware)
            logger.info("Telemetry before insert: type=registration hostname=%s device_uid=%s", hardware.get("hostname"), device_uid)
            send_register(hardware)
            logger.info("Telemetry after insert: type=registration hostname=%s device_uid=%s", hardware.get("hostname"), device_uid)
        except Exception as exc:
            logger.exception("Active application user-session registration failed; monitor will continue: %s", exc)
        self._seed_last_signature()
        self._write_status("started")
        logger.info("Active application user-session agent started.")
        return True

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            if STOP_PATH.exists():
                logger.info("Stop file detected before startup, stopping active application user-session agent.")
                self.stop_event.set()
                break
            if self.start():
                break
            self.stop_event.wait(STARTUP_RETRY_INTERVAL_SECONDS)

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
        try:
            latest = get_latest_active_application_for_host(hostname)
        except Exception as exc:
            logger.exception("Could not seed latest active application signature; monitor will continue: %s", exc)
            return
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
        try:
            _record_unlock_fallback_if_needed(record)
        except Exception as exc:
            logger.exception("Active application lock/unlock session fallback failed and will continue: %s", exc)
        if not record:
            self._write_status("running", foreground_visible=False)
            self._log_no_foreground_window()
            return

        hostname = record.get("hostname") or socket.gethostname()
        try:
            _log_activity_sample_state(record, "active_application_user_agent")
            send_activity_sample(record)
        except Exception as exc:
            logger.exception("Activity session sample failed and will continue: %s", exc)
        signature = _record_signature(record)
        activity_state = activity_state_from_record(record)
        same_foreground = self.last_signature_by_host.get(hostname) == signature
        same_activity_state = self.last_activity_state_by_host.get(hostname) == activity_state
        if same_foreground and same_activity_state:
            self._write_status("running", record=record, foreground_visible=True, inserted=False)
            return
        record["activity_state_changed"] = bool(same_foreground and not same_activity_state)

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
            send_application(record, record_sample=False)
            self.last_signature_by_host[hostname] = signature
            self.last_activity_state_by_host[hostname] = activity_state
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
                send_application(entry.get("payload") or {}, record_sample=False)
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
            "api_url": client().base_url,
            "foreground_diagnostics": collect_foreground_diagnostics(),
            "error": error,
        }
        try:
            STATUS_PATH.write_text(json.dumps(status, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.exception("Could not write active application user-session status file: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Asset Sentinel active application user-session agent.")
    parser.add_argument("--console", action="store_true", help="Log to stdout in addition to logs/agent.log.")
    args = parser.parse_args()

    configure_logging("agent", console=args.console)
    try:
        _acquire_single_instance()
    except SystemExit as exc:
        logger.error("Active application user-session agent did not start: %s", exc)
        raise
    except Exception as exc:
        logger.exception("Active application user-session single-instance guard failed: %s", exc)
        raise
    stop_event = threading.Event()

    def request_stop(signum, _frame):
        logger.info("Signal received, stopping active application user-session agent: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    while not stop_event.is_set():
        try:
            ActiveApplicationUserAgent(stop_event=stop_event).run_forever()
            break
        except Exception as exc:
            logger.exception("Active application user-session agent crashed at top level; restarting: %s", exc)
            if stop_event.wait(TOP_LEVEL_RESTART_INTERVAL_SECONDS):
                break


if __name__ == "__main__":
    main()
