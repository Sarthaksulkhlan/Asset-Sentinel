import argparse
import os
import sys
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parents[2]
for path in (ROOT_DIR / "agent" / "client", ROOT_DIR / "agent" / "collectors"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api_client import load_agent_env  # noqa: E402
from collect_hardware import collect_hardware  # noqa: E402


def _identity_payload() -> dict:
    hardware = collect_hardware()
    return {
        "hostname": hardware.get("hostname"),
        "uuid": hardware.get("uuid"),
        "bios_serial": hardware.get("bios_serial"),
        "baseboard_serial": hardware.get("baseboard_serial"),
        "mac_address": hardware.get("mac_address"),
        "composite_id": hardware.get("composite_id"),
        "collection_method": hardware.get("collection_method"),
    }


def _post(path: str, payload: dict) -> requests.Response:
    load_agent_env(force=True)
    api_url = (os.environ.get("ASSET_SENTINEL_API_URL") or "").rstrip("/")
    token = os.environ.get("ASSET_SENTINEL_AGENT_TOKEN") or ""
    return requests.post(
        f"{api_url}{path}",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Pair this Windows endpoint with an Asset Sentinel account.")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--otp")
    args = parser.parse_args()
    identity = _identity_payload()

    try:
        if args.status:
            response = _post("/api/agent/pairing/status", identity)
            response.raise_for_status()
            return 0 if response.json().get("paired") else 2

        if not args.otp:
            return 2
        response = _post("/api/agent/pair", {**identity, "otp": args.otp})
        if response.status_code >= 400:
            print("Invalid or Expired Pairing Code.")
            return 1
        if not response.json().get("paired"):
            print("Invalid or Expired Pairing Code.")
            return 1
        print("Device paired successfully.")
        return 0
    except requests.RequestException as exc:
        print(f"Device pairing service is unavailable: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
