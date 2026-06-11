# Asset Sentinel POC - ram_change_detector.py
# Detects RAM changes and alerts admin via console and email.
# Run: python ram_change_detector.py

import json
import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Configuration - loaded from .env file
# ---------------------------------------------------------------------------

ADMIN_EMAIL      = "sarthak2004sul@gmail.com"
SENDER_EMAIL     = "assetsentinel.alerts@gmail.com"
SENDER_PASSWORD  = "ogxpcoadvvneyrcg"
SMTP_HOST        = "smtp.gmail.com"
SMTP_PORT        = 587
ASSETS_FILE      = Path("assets.json")


# ---------------------------------------------------------------------------
# Load assets from file
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
# Detect RAM change
# ---------------------------------------------------------------------------

def detect_ram_change(previous, current):
    prev_ram = previous.get("ram_total_gb")
    curr_ram = current.get("ram_total_gb")

    if prev_ram is None or curr_ram is None:
        print("[WARNING] RAM data missing in one or both snapshots.")
        return None

    if prev_ram == curr_ram:
        return None

    return {
        "hostname": current.get("hostname", "Unknown"),
        "mac_address": current.get("mac_address", "Unknown"),
        "previous_ram": prev_ram,
        "current_ram": curr_ram,
        "difference_gb": round(curr_ram - prev_ram, 2),
        "detected_at": datetime.now().isoformat(),
        "previous_snapshot_time": previous.get("collected_at", "Unknown"),
        "current_snapshot_time": current.get("collected_at", "Unknown"),
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
    print(f"  MAC Address  : {change['mac_address']}")
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

    body = (
        "Asset Sentinel - RAM Change Alert\n"
        "===================================\n\n"
        "A RAM change has been detected on a monitored machine.\n\n"
        "Machine Details\n"
        "---------------\n"
        f"Hostname     : {change['hostname']}\n"
        f"MAC Address  : {change['mac_address']}\n\n"
        "RAM Change\n"
        "----------\n"
        f"Previous RAM : {change['previous_ram']} GB\n"
        f"Current RAM  : {change['current_ram']} GB\n"
        f"Change       : RAM has {direction} by {abs(change['difference_gb'])} GB\n\n"
        "Timestamps\n"
        "----------\n"
        f"Previous Snapshot : {change['previous_snapshot_time']}\n"
        f"Current Snapshot  : {change['current_snapshot_time']}\n"
        f"Alert Generated   : {change['detected_at']}\n\n"
        "This is an automated alert from Asset Sentinel.\n"
        "Please investigate this machine immediately."
    )

    if not all([ADMIN_EMAIL, SENDER_EMAIL, SENDER_PASSWORD]):
        print("[EMAIL ERROR] Missing email config in .env file.")
        return

    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = ADMIN_EMAIL
        message.attach(MIMEText(body, "plain"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, ADMIN_EMAIL, message.as_string())

        print(f"[EMAIL] Alert sent to {ADMIN_EMAIL}")

    except smtplib.SMTPAuthenticationError:
        print("[EMAIL ERROR] Authentication failed.")
        print("  Make sure you are using a Gmail App Password in your .env file.")
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
    current = assets[-1]

    print(f"[INFO] Comparing last 2 snapshots...")
    print(f"       Previous : {previous.get('collected_at', 'Unknown')} | RAM: {previous.get('ram_total_gb')} GB")
    print(f"       Current  : {current.get('collected_at', 'Unknown')} | RAM: {current.get('ram_total_gb')} GB")

    change = detect_ram_change(previous, current)

    if change is None:
        print("\n[OK] No RAM change detected. All good.")
        return

    print_alert(change)
    send_email_alert(change)


if __name__ == "__main__":
    run_detector()
