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
from storage import list_assets

try:
    assets = list_assets()
except Exception as exc:
    print(f"Could not load assets from PostgreSQL: {exc}")
    exit()

print(f"\nTotal Assets: {len(assets)}\n")

for i, asset in enumerate(assets, start=1):
    print("=" * 50)
    print("Hostname:", asset.get("hostname"))
    print("BIOS Serial:", asset.get("bios_serial"))
    print("Baseboard Serial:", asset.get("baseboard_serial"))
    print("Baseboard Manufacturer:", asset.get("baseboard_manufacturer"))
    print("IP Address:", asset.get("ip_address"))
    print("CPU:", asset.get("cpu_name"))
    
    print("RAM:", asset.get("ram_total_gb"), "GB")

