import argparse
import logging
import os
import signal
import threading

from database import database_host_for_display, init_db
from login_tracker import detect_login
from service_logging import configure_logging


logger = logging.getLogger("asset_sentinel.login_activity_agent")
LOGIN_POLL_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_LOGIN_POLL_SECONDS", "5"))


def run(stop_event: threading.Event) -> None:
    logger.info(
        "Login activity agent starting: interval_seconds=%s database_host=%s",
        LOGIN_POLL_INTERVAL_SECONDS,
        database_host_for_display(),
    )
    init_db()
    while not stop_event.is_set():
        try:
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
