import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend._bootstrap import bootstrap_paths

bootstrap_paths()

import login_tracker
import pairing


ROOT_DIR = Path(__file__).resolve().parents[2]


class LoginHistoryScopeTests(unittest.TestCase):
    def test_latest_sessions_are_scoped_to_current_hostname(self):
        sessions = [
            {
                "event_type": "LOGIN",
                "hostname": "CURRENT-PC",
                "login_source": "windows_interactive_logon",
                "windows_event_id": "4624",
                "windows_event_record_id": "100",
            },
            {
                "event_type": "LOGIN",
                "hostname": "OTHER-PC",
                "login_source": "windows_interactive_logon",
                "windows_event_id": "4624",
                "windows_event_record_id": "200",
            },
        ]

        with patch.object(login_tracker, "load_sessions", return_value=sessions):
            latest = login_tracker.get_last_recorded_session("CURRENT-PC")
            latest_countable = login_tracker.get_last_countable_login_session("CURRENT-PC")

        self.assertEqual(latest["windows_event_record_id"], "100")
        self.assertEqual(latest_countable["windows_event_record_id"], "100")

    def test_new_login_is_not_blocked_by_another_devices_latest_session(self):
        current_session = {
            "event_type": "LOGIN",
            "username": "CURRENT-PC\\user",
            "hostname": "CURRENT-PC",
            "session_id": "1",
            "login_timestamp": "2026-07-25T13:02:38+00:00",
            "login_source": "windows_interactive_logon",
            "windows_event_id": "4624",
            "windows_event_record_id": "101",
        }
        sessions = [
            {
                **current_session,
                "windows_event_record_id": "100",
                "login_timestamp": "2026-07-24T13:02:38+00:00",
            },
            {
                **current_session,
                "hostname": "OTHER-PC",
                "windows_event_record_id": "200",
            },
        ]

        with (
            patch.object(login_tracker, "get_current_session_info", return_value=current_session),
            patch.object(login_tracker, "load_sessions", return_value=sessions),
            patch.object(login_tracker, "_is_event_already_processed", return_value=False),
            patch.object(login_tracker, "has_session_event_signature", return_value=False),
            patch.object(login_tracker, "record_login", return_value=current_session) as record_login,
        ):
            result = login_tracker.detect_login()

        record_login.assert_called_once_with(current_session)
        self.assertEqual(result["windows_event_record_id"], "101")


class ExistingDeviceOwnershipTests(unittest.TestCase):
    def test_pairing_code_cannot_reassign_device_owned_by_another_user(self):
        code = SimpleNamespace(user_id=7)
        user = SimpleNamespace(id=7, is_active=True, company_id=2)
        asset = SimpleNamespace(owner_user_id=8)
        session = SimpleNamespace(
            execute=lambda _statement: SimpleNamespace(scalar_one_or_none=lambda: code),
            get=lambda _model, _identifier: user,
        )

        with (
            patch.object(pairing, "get_db_session", return_value=nullcontext(session)),
            patch.object(pairing, "_find_device", return_value=asset),
        ):
            result, status = pairing.pair_device({"otp": "4827"})

        self.assertEqual(status, 409)
        self.assertEqual(result["error"], "This device is already paired to another account.")


class InstallerContractTests(unittest.TestCase):
    def test_install_always_prompts_and_other_service_scripts_do_not(self):
        installer = (ROOT_DIR / "agent" / "scripts" / "install_service.bat").read_text(encoding="utf-8")
        self.assertIn("Enter your 4-digit Pairing Code:", installer)
        self.assertNotIn("pair_device.py --status", installer)

        for filename in (
            "restart_service.bat",
            "start_service.bat",
            "stop_service.bat",
            "uninstall_service.bat",
        ):
            script = (ROOT_DIR / "agent" / "scripts" / filename).read_text(encoding="utf-8")
            self.assertNotIn("Pairing Code", script)
            self.assertNotIn("pair_device.py", script)

    def test_active_application_verification_defaults_to_150_seconds(self):
        script = (ROOT_DIR / "agent" / "scripts" / "install_active_app_agent.bat").read_text(encoding="utf-8")
        self.assertIn('if not defined VERIFY_SECONDS set "VERIFY_SECONDS=150"', script)


if __name__ == "__main__":
    unittest.main()
