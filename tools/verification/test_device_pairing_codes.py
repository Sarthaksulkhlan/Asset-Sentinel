import unittest
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from backend._bootstrap import bootstrap_paths

bootstrap_paths()

import pairing
from models import Asset


class FakeResult:
    def __init__(self, one=None, values=None):
        self.one = one
        self.values = values or []

    def scalar_one_or_none(self):
        return self.one

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, results, user=None):
        self.results = list(results)
        self.user = user
        self.executed = []
        self.added = []

    def execute(self, statement):
        self.executed.append(statement)
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None

    def get(self, _model, _identifier):
        return self.user


class DevicePairingCodeTests(unittest.TestCase):
    def test_generate_invalidates_unused_code_and_expires_in_exactly_20_hours(self):
        now = datetime(2026, 7, 25, 10, 30, tzinfo=timezone.utc)
        session = FakeSession([
            FakeResult(),
            FakeResult(values=["4827"]),
            FakeResult(),
            FakeResult(one=None),
        ])

        with (
            patch.object(pairing, "get_db_session", return_value=nullcontext(session)),
            patch.object(pairing, "_utcnow", return_value=now),
            patch.object(pairing.secrets, "randbelow", side_effect=[4827, 7314]),
        ):
            result = pairing.issue_pairing_code(42)

        self.assertEqual(result["code"], "7314")
        self.assertEqual(result["createdAt"], now.isoformat())
        self.assertEqual(result["expiresAt"], (now + timedelta(hours=20)).isoformat())
        self.assertEqual(len(session.added), 1)
        self.assertIn("UPDATE device_pairing_codes", str(session.executed[2]))
        self.assertIn("usedisfalse", str(session.executed[2]).replace(" ", "").lower())
        update_params = session.executed[2].compile().params
        self.assertTrue(update_params["used"])
        self.assertEqual(update_params["used_at"], now)

    def test_get_returns_empty_state_without_generating_a_code(self):
        session = FakeSession([FakeResult(one=None)])
        with patch.object(pairing, "get_db_session", return_value=nullcontext(session)):
            result = pairing.get_pairing_code(42)

        self.assertEqual(result, {
            "code": None,
            "createdAt": None,
            "expiresAt": None,
            "used": False,
        })
        self.assertEqual(session.added, [])

    def test_pair_lookup_requires_unused_and_unexpired_code(self):
        session = FakeSession([FakeResult(one=None)])
        with patch.object(pairing, "get_db_session", return_value=nullcontext(session)):
            result, status = pairing.pair_device({"otp": "4827"})

        query = str(session.executed[0]).replace(" ", "").lower()
        self.assertEqual(status, 400)
        self.assertIn("usedisfalse", query)
        self.assertIn("expires_at>", query)
        self.assertEqual(result["error"], "Invalid or Expired Pairing Code.")

    def test_active_super_admin_can_pair_without_a_company(self):
        code = SimpleNamespace(
            code="4827",
            user_id=7,
            used=False,
            used_at=None,
            paired_device_uid=None,
        )
        user = SimpleNamespace(id=7, is_active=True, company_id=None)
        session = FakeSession([FakeResult(one=code)], user=user)

        with (
            patch.object(pairing, "get_db_session", return_value=nullcontext(session)),
            patch.object(pairing, "_find_device", return_value=None),
            patch.object(pairing, "resolve_device_uid", return_value="device-uid-7"),
        ):
            result, status = pairing.pair_device({"otp": "4827", "hostname": "ADMIN-PC"})

        asset = next(value for value in session.added if isinstance(value, Asset))
        self.assertEqual(status, 200)
        self.assertEqual(result["deviceUid"], "device-uid-7")
        self.assertIsNone(asset.company_id)
        self.assertEqual(asset.owner_user_id, 7)
        self.assertTrue(code.used)
        self.assertEqual(code.paired_device_uid, "device-uid-7")


if __name__ == "__main__":
    unittest.main()
