import threading
import time

from config import Config
from monitoring_agent import AssetSentinelAgent
from session_manager import get_current_hostname
from storage import get_asset_status


def _status(hostname: str) -> str:
    return (get_asset_status(hostname) or {}).get("device_status", "Missing")


def main() -> int:
    hostname = get_current_hostname()
    stop_event = threading.Event()
    agent = AssetSentinelAgent(stop_event=stop_event)
    agent.start()
    time.sleep(5)
    online_status = _status(hostname)
    agent.stop(timeout=10)

    wait_seconds = Config.HEARTBEAT_TIMEOUT_SECONDS + Config.HEARTBEAT_FUTURE_SKEW_SECONDS + 2
    time.sleep(wait_seconds)
    offline_status = _status(hostname)

    print(f"Hostname: {hostname}")
    print(f"Status while agent running: {online_status}")
    print(f"Status after {wait_seconds}s without heartbeat: {offline_status}")
    if online_status != "Online" or offline_status != "Offline":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
