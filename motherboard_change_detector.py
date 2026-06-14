import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ADMIN_EMAIL     = "sarthak2004sul@gmail.com"
SENDER_EMAIL    = "assetsentinel.alerts@gmail.com"
SENDER_PASSWORD = "wgvpxmwdyfjrspqw"
SMTP_HOST       = "smtp.gmail.com"
SMTP_PORT       = 587
ASSETS_FILE     = Path("assets.json")
ALERTS_FILE     = Path("alerts.json")


# ---------------------------------------------------------------------------
# Alert helpers - reusable across all detectors
# ---------------------------------------------------------------------------

def load_alerts():
    """Load existing alerts from alerts.json. Returns empty list if file does not exist."""
    if not ALERTS_FILE.exists():
        return []
    try:
        content = ALERTS_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[WARNING] Could not read alerts.json: {e}")
        return []


def save_alert(alert_type, hostname, severity, details):
    """
    Append a new alert record to alerts.json.
    Creates the file if it does not exist.

    Parameters:
        alert_type : str  - e.g. "MOTHERBOARD_CHANGE"
        hostname   : str  - machine hostname
        severity   : str  - "LOW", "MEDIUM", "HIGH", "CRITICAL"
        details    : dict - alert-specific data
    """
    alerts = load_alerts()

    record = {
        "alert_type": alert_type,
        "hostname":   hostname,
        "severity":   severity,
        "timestamp":  datetime.now().isoformat(),
        "details":    details,
    }

    alerts.append(record)

    try:
        ALERTS_FILE.write_text(
            json.dumps(alerts, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"[ALERT LOG] Incident saved to alerts.json")
    except Exception as e:
        print(f"[WARNING] Could not write to alerts.json: {e}")


# ---------------------------------------------------------------------------
# Load assets
# ---------------------------------------------------------------------------

def load_assets():
    if not ASSETS_FILE.exists():
        print("[ERROR] assets.json not found. Run save_hardware.py first.")
        return []
    try:
        content = ASSETS_FILE.read_text(encoding="utf-8").strip()
        if not content:
            print("[ERROR] assets.json is empty.")
            return []
        data = json.loads(content)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[ERROR] Could not read assets.json: {e}")
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

    body = (
        "Asset Sentinel - CRITICAL Motherboard Change Alert\n"
        "====================================================\n\n"
        "A motherboard change has been detected on a monitored machine.\n"
        "This may indicate hardware tampering or an unauthorized replacement.\n\n"
        "Machine Details\n"
        "---------------\n"
        f"Hostname              : {change['hostname']}\n"
        f"IP Address            : {change['ip_address']}\n"
        f"Detection Time        : {change['detected_at']}\n\n"
        "BIOS Serial\n"
        "-----------\n"
        f"Previous              : {change['prev_bios_serial'] or 'N/A'}\n"
        f"Current               : {change['curr_bios_serial'] or 'N/A'}\n"
        f"Changed               : {'YES' if change['bios_changed'] else 'NO'}\n\n"
        "Baseboard Serial\n"
        "----------------\n"
        f"Previous              : {change['prev_baseboard_serial'] or 'N/A'}\n"
        f"Current               : {change['curr_baseboard_serial'] or 'N/A'}\n"
        f"Changed               : {'YES' if change['baseboard_changed'] else 'NO'}\n\n"
        "Snapshot Timestamps\n"
        "-------------------\n"
        f"Previous Snapshot     : {change['previous_snapshot_time']}\n"
        f"Current Snapshot      : {change['current_snapshot_time']}\n\n"
        "This is an automated critical alert from Asset Sentinel.\n"
        "Please investigate this machine immediately."
    )

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"]    = SENDER_EMAIL
        message["To"]      = ADMIN_EMAIL
        message.attach(MIMEText(body, "plain"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, ADMIN_EMAIL, message.as_string())

        print(f"[EMAIL] Critical alert sent to {ADMIN_EMAIL}")

    except smtplib.SMTPAuthenticationError:
        print("[EMAIL ERROR] Authentication failed.")
        print("  Make sure SENDER_PASSWORD is a valid Gmail App Password.")
        print("  Generate one at: https://myaccount.google.com/apppasswords")
    except smtplib.SMTPException as e:
        print(f"[EMAIL ERROR] SMTP error: {e}")
    except Exception as e:
        print(f"[EMAIL ERROR] Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_detector():
    assets = load_assets()

    if len(assets) < 2:
        print(f"[INFO] Need at least 2 snapshots to compare.")
        print(f"       Currently have {len(assets)} snapshot(s) in assets.json.")
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

    # Motherboard changed - print alert, log to alerts.json, send email
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

    send_email_alert(change)


if __name__ == "__main__":
    run_detector()