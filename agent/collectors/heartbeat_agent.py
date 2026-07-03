import argparse
import logging
import signal
import socket
import sys
import threading
import time
import os
from typing import Any
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
from service_logging import configure_logging
from collect_hardware import collect_hardware
from storage import resolve_device_uid, upsert_asset, update_asset_heartbeat


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
    device_uid = None
    try:
        hardware = collect_hardware()
        hostname = hardware.get("hostname") or hostname
        device_uid = resolve_device_uid(hardware)
        logger.info("Telemetry before insert: type=registration hostname=%s device_uid=%s", hostname, device_uid)
        upsert_asset(hardware)
        logger.info("Telemetry after insert: type=registration hostname=%s device_uid=%s", hostname, device_uid)
    except Exception as exc:
        logger.exception("Heartbeat agent registration failed; heartbeat will auto-register fallback asset: %s", exc)
    while not stop_event.is_set():
        try:
            cpu_usage, ram_usage = _usage_snapshot()
            update_asset_heartbeat(hostname, cpu_usage, ram_usage, {"device_uid": device_uid} if device_uid else None)
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
