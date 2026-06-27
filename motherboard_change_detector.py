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
        alert_type : str  - e.g. "MOTHERBOARD_CHANGE"
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
# Detect motherboard change
# ---------------------------------------------------------------------------

def detect_motherboard_change(previous, current):
    """
    Compare bios_serial and baseboard_serial between two snapshots.
    Returns a change dict if either value changed, None if unchanged.
    """
    prev_bios      = previous.get("bios_serial")
    curr_bios      = current.get("bios_serial")
    prev_baseboard = previous.get("baseboard_serial")
    curr_baseboard = current.get("baseboard_serial")

    bios_changed      = (prev_bios != curr_bios)
    baseboard_changed = (prev_baseboard != curr_baseboard)

    if not bios_changed and not baseboard_changed:
        return None

    return {
        "hostname":               current.get("hostname", "Unknown"),
        "ip_address":             current.get("ip_address", "Unknown"),
        "prev_bios_serial":       prev_bios,
        "curr_bios_serial":       curr_bios,
        "prev_baseboard_serial":  prev_baseboard,
        "curr_baseboard_serial":  curr_baseboard,
        "bios_changed":           bios_changed,
        "baseboard_changed":      baseboard_changed,
        "detected_at":            datetime.now().isoformat(),
        "previous_snapshot_time": previous.get("collected_at", "Unknown"),
        "current_snapshot_time":  current.get("collected_at", "Unknown"),
    }


# ---------------------------------------------------------------------------
# Print alert to console
# ---------------------------------------------------------------------------

def print_alert(change):
    print()
    print("=" * 70)
    print("  CRITICAL - ASSET SENTINEL - MOTHERBOARD CHANGE DETECTED")
    print("=" * 70)
    print(f"  Hostname              : {change['hostname']}")
    print(f"  IP Address            : {change['ip_address']}")
    print(f"  Detected At           : {change['detected_at']}")
    print()
    print("  BIOS Serial")
    print(f"    Previous            : {change['prev_bios_serial'] or 'N/A'}")
    print(f"    Current             : {change['curr_bios_serial'] or 'N/A'}")
    print(f"    Changed             : {'YES' if change['bios_changed'] else 'NO'}")
    print()
    print("  Baseboard Serial")
    print(f"    Previous            : {change['prev_baseboard_serial'] or 'N/A'}")
    print(f"    Current             : {change['curr_baseboard_serial'] or 'N/A'}")
    print(f"    Changed             : {'YES' if change['baseboard_changed'] else 'NO'}")
    print()
    print("  ACTION REQUIRED: Investigate this machine immediately.")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Send email alert
# ---------------------------------------------------------------------------

def send_email_alert(change):
    subject = "[CRITICAL] Motherboard Change Detected - Asset Sentinel"
    sent = send_alert_email(subject, {
        "Hostname": change["hostname"],
        "IP Address": change["ip_address"],
        "Detection Time": change["detected_at"],
        "Previous BIOS Serial": change["prev_bios_serial"] or "N/A",
        "Current BIOS Serial": change["curr_bios_serial"] or "N/A",
        "BIOS Changed": "YES" if change["bios_changed"] else "NO",
        "Previous Baseboard Serial": change["prev_baseboard_serial"] or "N/A",
        "Current Baseboard Serial": change["curr_baseboard_serial"] or "N/A",
        "Baseboard Changed": "YES" if change["baseboard_changed"] else "NO",
        "Previous Snapshot": change["previous_snapshot_time"],
        "Current Snapshot": change["current_snapshot_time"],
    })
    if sent:
        print("[EMAIL] Motherboard change alert sent")
    else:
        print("[EMAIL ERROR] Motherboard change alert was saved but email notification failed")


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

    print(f"[INFO] Comparing last 2 snapshots for motherboard changes...")
    print(f"       Previous : {previous.get('collected_at', 'Unknown')}")
    print(f"                  BIOS: {previous.get('bios_serial', 'N/A')} | Baseboard: {previous.get('baseboard_serial', 'N/A')}")
    print(f"       Current  : {current.get('collected_at', 'Unknown')}")
    print(f"                  BIOS: {current.get('bios_serial', 'N/A')} | Baseboard: {current.get('baseboard_serial', 'N/A')}")

    change = detect_motherboard_change(previous, current)

    if change is None:
        print("\n[OK] No motherboard change detected. All good.")
        return

    # Motherboard changed - print alert, log to PostgreSQL, send email
    print_alert(change)

    save_alert(
        alert_type = "MOTHERBOARD_CHANGE",
        hostname   = change["hostname"],
        severity   = "CRITICAL",
        details    = {
            "ip_address":             change["ip_address"],
            "prev_bios_serial":       change["prev_bios_serial"],
            "curr_bios_serial":       change["curr_bios_serial"],
            "prev_baseboard_serial":  change["prev_baseboard_serial"],
            "curr_baseboard_serial":  change["curr_baseboard_serial"],
            "bios_changed":           change["bios_changed"],
            "baseboard_changed":      change["baseboard_changed"],
            "previous_snapshot_time": change["previous_snapshot_time"],
            "current_snapshot_time":  change["current_snapshot_time"],
        }
    )

    try:
        record_hardware_change(
            hostname=change["hostname"],
            change_type="MOTHERBOARD_CHANGE",
            severity="CRITICAL",
            previous_value={
                "bios_serial": change["prev_bios_serial"],
                "baseboard_serial": change["prev_baseboard_serial"],
            },
            current_value={
                "bios_serial": change["curr_bios_serial"],
                "baseboard_serial": change["curr_baseboard_serial"],
            },
            difference={
                "bios_changed": change["bios_changed"],
                "baseboard_changed": change["baseboard_changed"],
            },
            detected_at=change["detected_at"],
        )
    except Exception as e:
        print(f"[WARNING] Could not save hardware change to PostgreSQL: {e}")

    send_email_alert(change)


if __name__ == "__main__":
    run_detector()
