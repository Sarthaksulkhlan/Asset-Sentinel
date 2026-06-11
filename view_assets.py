import json
from pathlib import Path

ASSETS_FILE = Path("assets.json")

if not ASSETS_FILE.exists():
    print("No assets found")
    exit()

with open(ASSETS_FILE, "r", encoding="utf-8") as f:
    assets = json.load(f)

print(f"\nTotal Assets: {len(assets)}\n")

for i, asset in enumerate(assets, start=1):
    print("=" * 50)
    print(f"Asset #{i}")
    print("Hostname:", asset.get("hostname"))
    print("BIOS Serial:", asset.get("bios_serial"))
    print("IP Address:", asset.get("ip_address"))
    print("CPU:", asset.get("cpu_name"))
    print("RAM:", asset.get("ram_total_gb"), "GB")