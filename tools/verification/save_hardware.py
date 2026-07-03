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
from collect_hardware import collect_hardware
from storage import list_assets, resolve_device_uid, upsert_asset


def load_existing_assets():
    try:
        return list_assets()
    except Exception as exc:
        print(f"[ERROR] Could not load assets from PostgreSQL: {exc}")
        return []


def save_hardware():
    hardware = collect_hardware()
    assets = load_existing_assets()

    current_uid = resolve_device_uid(hardware)
    exists = False

    for asset in assets:
        if asset.get("device_uid") == current_uid:
            exists = True
            break

    upsert_asset(hardware)
    print("Asset updated" if exists else "New asset added")

    print("Asset saved successfully")


if __name__ == "__main__":
    save_hardware()

