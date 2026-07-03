from pathlib import Path
import sys

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
]:
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)
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

