import argparse
import logging
import os
import signal
import sys
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
for path in [
    ROOT_DIR,
    ROOT_DIR / "backend" / "api",
    ROOT_DIR / "backend" / "core",
    ROOT_DIR / "backend" / "models",
    ROOT_DIR / "backend" / "services",
    ROOT_DIR / "agent" / "collectors",
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from database import database_host_for_display, init_db
from collect_hardware import collect_hardware
from active_application_monitor import _record_unlock_fallback_if_needed, collect_active_application_record
from login_tracker import detect_login
from service_logging import configure_logging
from storage import resolve_device_uid, upsert_asset


logger = logging.getLogger("asset_sentinel.login_activity_agent")
LOGIN_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_LOGIN_POLL_SECONDS", "1"))


def run(stop_event: threading.Event) -> None:
    logger.info(
        "Login activity agent starting: interval_seconds=%s database_host=%s",
        LOGIN_POLL_INTERVAL_SECONDS,
        database_host_for_display(),
    )
    init_db()
    try:
        hardware = collect_hardware()
        device_uid = resolve_device_uid(hardware)
        logger.info("Telemetry before insert: type=registration hostname=%s device_uid=%s", hardware.get("hostname"), device_uid)
        upsert_asset(hardware)
        logger.info("Telemetry after insert: type=registration hostname=%s device_uid=%s", hardware.get("hostname"), device_uid)
    except Exception as exc:
        logger.exception("Login activity agent registration failed; login tracker will continue: %s", exc)
    while not stop_event.is_set():
        try:
            logger.info("Telemetry before insert: type=login_activity")
            try:
                _record_unlock_fallback_if_needed(collect_active_application_record())
            except Exception as fallback_exc:
                logger.exception("Login activity lock/unlock fallback failed and will continue: %s", fallback_exc)
            record = detect_login()
            if record:
                logger.info(
                    "Login database insert confirmed: user=%s host=%s source=%s event_id=%s record_id=%s",
                    record.get("username"),
                    record.get("hostname"),
                    record.get("login_source"),
                    record.get("windows_event_id"),
                    record.get("windows_event_record_id"),
                )
                logger.info("Telemetry after insert: type=login_activity hostname=%s record_id=%s", record.get("hostname"), record.get("windows_event_record_id"))
        except Exception as exc:
            logger.exception("Login activity polling failed and will retry: %s", exc)
        stop_event.wait(LOGIN_POLL_INTERVAL_SECONDS)
    logger.info("Login activity agent stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Asset Sentinel login activity agent.")
    parser.add_argument("--console", action="store_true", help="Log to stdout in addition to logs/agent.log.")
    args = parser.parse_args()

    configure_logging("agent", console=args.console)
    stop_event = threading.Event()

    def request_stop(signum, _frame):
        logger.info("Signal received, stopping login activity agent: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    run(stop_event)


if __name__ == "__main__":
    main()
