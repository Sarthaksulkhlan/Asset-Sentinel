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
