import unittest

from agent.client import api_client
from agent.client.api_client import _activity_state


class LockProductivityStateTests(unittest.TestCase):
    def test_explicit_windows_lock_is_locked(self):
        self.assertEqual(
            _activity_state({"application_name": "chrome", "windows_locked": True}),
            "LOCKED",
        )

    def test_lockapp_foreground_is_locked_when_desktop_probe_is_false(self):
        self.assertEqual(
            _activity_state({
                "application_name": "LockApp",
                "executable_name": "LockApp.exe",
                "window_title": "Windows Lock Screen",
                "windows_locked": False,
                "is_user_idle": False,
            }),
            "LOCKED",
        )

    def test_lock_screen_takes_priority_over_idle(self):
        self.assertEqual(
            _activity_state({
                "application_name": "LockApp",
                "windows_locked": False,
                "is_user_idle": True,
            }),
            "LOCKED",
        )

    def test_non_lock_idle_and_active_states_are_unchanged(self):
        self.assertEqual(
            _activity_state({"application_name": "chrome", "is_user_idle": True}),
            "IDLE",
        )
        self.assertEqual(
            _activity_state({"application_name": "chrome", "is_user_idle": False}),
            "ACTIVE",
        )

    def test_lock_interval_pauses_active_work_and_unlock_resumes_it(self):
        api_client._activity_usage_buffer.clear()
        active = {
            "hostname": "DevrishiBhardwaj",
            "username": "user",
            "application_name": "chrome",
            "window_title": "Browser",
            "timestamp": "2026-07-23T06:00:00+00:00",
            "windows_locked": False,
            "is_user_idle": False,
        }
        locked = {
            **active,
            "application_name": "LockApp",
            "executable_name": "LockApp.exe",
            "window_title": "Windows Lock Screen",
            "timestamp": "2026-07-23T06:00:10+00:00",
        }
        still_locked = {**locked, "timestamp": "2026-07-23T06:00:20+00:00"}
        unlocked = {**active, "timestamp": "2026-07-23T06:00:30+00:00"}
        active_again = {**active, "timestamp": "2026-07-23T06:00:40+00:00"}

        api_client._buffer_activity_interval(active, locked)
        api_client._buffer_activity_interval(locked, still_locked)
        api_client._buffer_activity_interval(still_locked, unlocked)
        api_client._buffer_activity_interval(unlocked, active_again)

        totals = {"ACTIVE": 0, "IDLE": 0, "LOCKED": 0}
        for record in api_client._activity_usage_buffer.values():
            totals[record["state"]] += record["duration_seconds"]

        self.assertEqual(totals, {"ACTIVE": 20, "IDLE": 0, "LOCKED": 20})
        api_client._activity_usage_buffer.clear()


if __name__ == "__main__":
    unittest.main()
