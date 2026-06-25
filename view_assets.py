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
