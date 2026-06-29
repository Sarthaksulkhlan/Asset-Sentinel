import threading
import time

from monitoring_agent import AssetSentinelAgent
from storage import get_asset_status, get_latest_active_application_for_host
from session_manager import get_current_hostname


def main() -> int:
    hostname = get_current_hostname()
    stop_event = threading.Event()
    agent = AssetSentinelAgent(stop_event=stop_event)
    agent.start()
    time.sleep(5)
    agent.stop(timeout=10)

    status = get_asset_status(hostname) or {}
    latest_activity = get_latest_active_application_for_host(hostname)
    print(f"Hostname: {hostname}")
    print(f"Status after agent heartbeat: {status.get('device_status')}")
    print(f"Last seen: {status.get('last_seen')}")
    print(f"Latest active application: {(latest_activity or {}).get('application_name')}")
    print(f"Latest active window: {(latest_activity or {}).get('window_title')}")
    if status.get("device_status") != "Online":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
