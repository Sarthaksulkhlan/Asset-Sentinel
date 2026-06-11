import json
from pathlib import Path

from collect_hardware import collect_hardware

ASSETS_FILE = Path("assets.json")


def load_existing_assets():
    if not ASSETS_FILE.exists():
        return []

    try:
        return json.loads(
            ASSETS_FILE.read_text(encoding="utf-8")
        )
    except:
        return []


def save_hardware():
    hardware = collect_hardware()
    assets = load_existing_assets()

    exists = False

    for asset in assets:
        if asset.get("bios_serial") == hardware.get("bios_serial"):
            exists = True
            break

    if not exists:
        assets.append(hardware)
        print("New asset added")
    else:
        print("Asset already exists")

    ASSETS_FILE.write_text(
        json.dumps(assets, indent=2),
        encoding="utf-8"
    )

    print("Asset saved successfully")


if __name__ == "__main__":
    save_hardware()