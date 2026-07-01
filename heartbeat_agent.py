import argparse
import logging
import signal
import socket
import threading
import time
import os
from typing import Any

from database import database_host_for_display, init_db
from service_logging import configure_logging
from storage import update_asset_heartbeat


logger = logging.getLogger("asset_sentinel.heartbeat_agent")
HEARTBEAT_INTERVAL_SECONDS = int(os.environ.get("ASSET_SENTINEL_HEARTBEAT_POLL_SECONDS", "2"))


def _usage_snapshot() -> tuple[Any, Any]:
    try:
        import psutil

        return round(float(psutil.cpu_percent(interval=None)), 2), round(float(psutil.virtual_memory().percent), 2)
    except Exception:
        return None, None


def run(stop_event: threading.Event) -> None:
    hostname = socket.gethostname()
    logger.info("Heartbeat agent starting: hostname=%s database_host=%s", hostname, database_host_for_display())
    init_db()
    while not stop_event.is_set():
        try:
            cpu_usage, ram_usage = _usage_snapshot()
            update_asset_heartbeat(hostname, cpu_usage, ram_usage, None)
            logger.info(
                "Heartbeat sent: hostname=%s interval_seconds=%s cpu=%s ram=%s",
                hostname,
                HEARTBEAT_INTERVAL_SECONDS,
                cpu_usage,
                ram_usage,
            )
        except Exception as exc:
            logger.exception("Heartbeat failed and will retry: %s", exc)
        stop_event.wait(HEARTBEAT_INTERVAL_SECONDS)
    logger.info("Heartbeat agent stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Asset Sentinel heartbeat-only agent.")
    parser.add_argument("--console", action="store_true", help="Log to stdout in addition to logs/agent.log.")
    args = parser.parse_args()

    configure_logging("agent", console=args.console)
    stop_event = threading.Event()

    def request_stop(signum, _frame):
        logger.info("Signal received, stopping heartbeat agent: %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    run(stop_event)


if __name__ == "__main__":
    main()
