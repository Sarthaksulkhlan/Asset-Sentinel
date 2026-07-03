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
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from config import Config
from database import database_host_for_display
from storage import (
    _status_from_last_seen,
    identity_candidates,
    merge_duplicate_assets,
    resolve_device_uid,
)
from session_manager import get_latest_windows_login_event, get_latest_windows_logout_event


class FakeEvent:
    def __init__(self, event_id, record_number, inserts):
        self.EventID = event_id
        self.RecordNumber = record_number
        self.StringInserts = inserts
        self.TimeGenerated = datetime.now(timezone.utc)


class FakeEventLog:
    EVENTLOG_BACKWARDS_READ = 0x0008
    EVENTLOG_SEQUENTIAL_READ = 0x0001

    def __init__(self, events):
        self.events = events
        self.read = False

    def OpenEventLog(self, *_args):
        return object()

    def ReadEventLog(self, *_args):
        if self.read:
            return []
        self.read = True
        return self.events

    def CloseEventLog(self, *_args):
        return None


def verify_identity_resolution():
    record_a = {
        "hostname": "DevrishiBhardwaj",
        "uuid": "7b53e8e5-047c-485a-9a5d-cf403b22a2d7",
        "bios_serial": "BIOS-1",
        "baseboard_serial": "BOARD-1",
    }
    record_b = {**record_a, "hostname": "RenamedHost"}
    assert resolve_device_uid(record_a) == resolve_device_uid(record_b)
    assert identity_candidates({"hostname": "OnlyHost", "bios_serial": "To Be Filled By O.E.M."}) == []


def verify_dynamic_status():
    timeout = Config.HEARTBEAT_TIMEOUT_SECONDS
    assert _status_from_last_seen(datetime.now(timezone.utc)) == "Online"
    assert _status_from_last_seen(datetime.now(timezone.utc) - timedelta(seconds=timeout + 5)) == "Offline"
    assert _status_from_last_seen(None) == "Offline"


def verify_duplicate_merge_logic():
    owner = SimpleNamespace(
        id=1,
        device_uid="uuid-1",
        hostname="DevrishiBhardwaj",
        ip_address=None,
        mac_address="aa",
        bios_serial="bios-1",
        baseboard_serial="board-1",
        uuid=None,
        composite_id=None,
        cpu_name=None,
        ram_total_gb=None,
        baseboard_manufacturer=None,
        baseboard_product=None,
        windows_version=None,
        current_website=None,
        active_window_title=None,
        active_process_path=None,
        active_process_name=None,
        cpu_usage_percent=None,
        ram_usage_percent=None,
        collection_method="uuid",
        collection_errors=[],
        collected_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        last_seen=datetime.now(timezone.utc) - timedelta(minutes=2),
    )
    duplicate = SimpleNamespace(**{**owner.__dict__, "id": 2, "hostname": "DevrishiBhardwaj", "last_seen": datetime.now(timezone.utc)})

    class FakeSession:
        def __init__(self):
            self.deleted = []

        def execute(self, statement):
            text = str(statement)
            if "SELECT" in text and "FROM assets" in text:
                return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [owner, duplicate]))
            return SimpleNamespace()

        def get(self, _model, row_id):
            return duplicate if row_id == 2 else owner

        def delete(self, row):
            self.deleted.append(row.id)

    session = FakeSession()
    assert merge_duplicate_assets(session) == 1
    assert session.deleted == [2]


def verify_windows_event_audit():
    login_inserts = ["", "", "", "", "", "Devrishi", "", "", "2"]
    unlock_inserts = ["", "", "", "", "", "Devrishi", "", "", "7"]
    logout_inserts = ["", "", "", "", "", "Devrishi"]
    with patch("session_manager.os.name", "nt"), patch("session_manager.win32evtlog", FakeEventLog([
        FakeEvent(4624, 100, login_inserts),
    ])):
        login_event = get_latest_windows_login_event("Devrishi")
    assert login_event["event_id"] == "4624"
    assert login_event["login_source"] == "windows_interactive_logon"

    with patch("session_manager.os.name", "nt"), patch("session_manager.win32evtlog", FakeEventLog([
        FakeEvent(4801, 101, unlock_inserts),
    ])):
        unlock_as_login = get_latest_windows_login_event("Devrishi")
    assert unlock_as_login is None

    with patch("session_manager.os.name", "nt"), patch("session_manager.win32evtlog", FakeEventLog([
        FakeEvent(4800, 102, logout_inserts),
    ])):
        logout_event = get_latest_windows_logout_event("Devrishi")
    assert logout_event["event_id"] == "4800"
    assert logout_event["login_source"] == "windows_lock"


def verify_database_target():
    host = database_host_for_display()
    assert host not in {"localhost", "127.0.0.1", "::1", "unknown"}
    print(f"Database host from ASSET_SENTINEL_DATABASE_URL: {host}")


if __name__ == "__main__":
    verify_identity_resolution()
    verify_dynamic_status()
    verify_duplicate_merge_logic()
    verify_windows_event_audit()
    verify_database_target()
    print("Asset Sentinel fix verification passed.")

