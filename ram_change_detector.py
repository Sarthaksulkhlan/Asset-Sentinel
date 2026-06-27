from datetime import datetime

from notifications import send_alert_email
from storage import append_alert, list_alerts, list_assets, record_hardware_change


# ---------------------------------------------------------------------------
# Alert helpers - reusable across all detectors
# ---------------------------------------------------------------------------

def load_alerts():
    """Load existing alerts from PostgreSQL. Returns empty list if unavailable."""
    try:
        return list_alerts()
    except Exception as e:
        print(f"[WARNING] Could not read alerts from PostgreSQL: {e}")
        return []


def save_alert(alert_type, hostname, severity, details):
    """
    Append a new alert record to PostgreSQL.

    Parameters:
        alert_type : str  - e.g. "RAM_CHANGE"
        hostname   : str  - machine hostname
        severity   : str  - "LOW", "MEDIUM", "HIGH", "CRITICAL"
        details    : dict - alert-specific data
    """
    try:
        append_alert(alert_type, hostname, severity, details, datetime.now().isoformat())
        print(f"[ALERT LOG] Incident saved to PostgreSQL")
    except Exception as e:
        print(f"[WARNING] Could not write alert to PostgreSQL: {e}")


# ---------------------------------------------------------------------------
# Load assets
# ---------------------------------------------------------------------------

def load_assets():
    try:
        data = list_assets()
        if not data:
            print("[ERROR] No assets found in PostgreSQL. Run save_hardware.py first.")
            return []
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[ERROR] Could not read assets from PostgreSQL: {e}")
        return []


# ---------------------------------------------------------------------------
# Detect RAM change
# ---------------------------------------------------------------------------

def detect_ram_change(previous, current):
    """
    Compare ram_total_gb between two snapshots.
    Returns a change dict if RAM changed, None if unchanged.
    """
    prev_ram = previous.get("ram_total_gb")
    curr_ram = current.get("ram_total_gb")

    if prev_ram is None or curr_ram is None:
        print("[WARNING] RAM data missing in one or both snapshots.")
        return None

    if prev_ram == curr_ram:
        return None

    return {
        "hostname":               current.get("hostname", "Unknown"),
        "ip_address":             current.get("ip_address", "Unknown"),
        "previous_ram":           prev_ram,
        "current_ram":            curr_ram,
        "difference_gb":          round(curr_ram - prev_ram, 2),
        "detected_at":            datetime.now().isoformat(),
        "previous_snapshot_time": previous.get("collected_at", "Unknown"),
        "current_snapshot_time":  current.get("collected_at", "Unknown"),
    }


# ---------------------------------------------------------------------------
# Print alert to console
# ---------------------------------------------------------------------------

def print_alert(change):
    direction = "INCREASED" if change["difference_gb"] > 0 else "DECREASED"
    print()
    print("=" * 60)
    print("  WARNING - ASSET SENTINEL - RAM CHANGE DETECTED")
    print("=" * 60)
    print(f"  Hostname     : {change['hostname']}")
    print(f"  IP Address   : {change['ip_address']}")
    print(f"  Previous RAM : {change['previous_ram']} GB")
    print(f"  Current RAM  : {change['current_ram']} GB")
    print(f"  Change       : {direction} by {abs(change['difference_gb'])} GB")
    print(f"  Detected At  : {change['detected_at']}")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Send email alert
# ---------------------------------------------------------------------------

def send_email_alert(change):
    direction = "increased" if change["difference_gb"] > 0 else "decreased"

    subject = f"[Asset Sentinel] RAM Change Detected on {change['hostname']}"
    sent = send_alert_email(subject, {
        "Hostname": change["hostname"],
        "IP Address": change["ip_address"],
        "Previous RAM": f"{change['previous_ram']} GB",
        "Current RAM": f"{change['current_ram']} GB",
        "Change": f"RAM has {direction} by {abs(change['difference_gb'])} GB",
        "Previous Snapshot": change["previous_snapshot_time"],
        "Current Snapshot": change["current_snapshot_time"],
        "Alert Generated": change["detected_at"],
    })
    if sent:
        print("[EMAIL] RAM change alert sent")
    else:
        print("[EMAIL ERROR] RAM change alert was saved but email notification failed")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_detector():
    assets = load_assets()

    if len(assets) < 2:
        print(f"[INFO] Need at least 2 snapshots to compare.")
        print(f"       Currently have {len(assets)} snapshot(s) in PostgreSQL.")
        print("       Run save_hardware.py again to add another snapshot.")
        return

    previous = assets[-2]
    current  = assets[-1]

    print(f"[INFO] Comparing last 2 snapshots...")
    print(f"       Previous : {previous.get('collected_at', 'Unknown')} | RAM: {previous.get('ram_total_gb')} GB")
    print(f"       Current  : {current.get('collected_at', 'Unknown')} | RAM: {current.get('ram_total_gb')} GB")

    change = detect_ram_change(previous, current)

    if change is None:
        print("\n[OK] No RAM change detected. All good.")
        return

    # RAM changed - print alert, log to PostgreSQL, send email
    print_alert(change)

    save_alert(
        alert_type = "RAM_CHANGE",
        hostname   = change["hostname"],
        severity   = "HIGH",
        details    = {
            "ip_address":             change["ip_address"],
            "previous_ram_gb":        change["previous_ram"],
            "current_ram_gb":         change["current_ram"],
            "difference_gb":          change["difference_gb"],
            "previous_snapshot_time": change["previous_snapshot_time"],
            "current_snapshot_time":  change["current_snapshot_time"],
        }
    )

    try:
        record_hardware_change(
            hostname=change["hostname"],
            change_type="RAM_CHANGE",
            severity="HIGH",
            previous_value={"ram_total_gb": change["previous_ram"]},
            current_value={"ram_total_gb": change["current_ram"]},
            difference={"difference_gb": change["difference_gb"]},
            detected_at=change["detected_at"],
        )
    except Exception as e:
        print(f"[WARNING] Could not save hardware change to PostgreSQL: {e}")

    send_email_alert(change)


if __name__ == "__main__":
    run_detector()
