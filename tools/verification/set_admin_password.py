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
import argparse
import getpass
from datetime import datetime, timezone

from sqlalchemy import func, or_, select

from auth import hash_password
from database import get_db_session, init_db
from models import RefreshToken, User


def set_password(identifier: str, new_password: str) -> bool:
    normalized = identifier.strip().lower()
    with get_db_session() as session:
        user = session.execute(
            select(User)
            .where(or_(func.lower(User.username) == normalized, func.lower(User.email) == normalized))
            .limit(1)
        ).scalar_one_or_none()

        if not user:
            return False

        user.password_hash = hash_password(new_password)
        user.is_active = True

        session.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.user_id == user.id)
            .where(RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset an Asset Sentinel user's password.")
    parser.add_argument(
        "identifier",
        nargs="?",
        default="sentinelcommand",
        help="Username or email to reset. Defaults to sentinelcommand.",
    )
    args = parser.parse_args()

    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        raise SystemExit("Passwords do not match.")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters.")

    init_db()
    if not set_password(args.identifier, password):
        raise SystemExit(f"User not found: {args.identifier}")

    print(f"Password updated for {args.identifier}. Existing refresh sessions were logged out.")


if __name__ == "__main__":
    main()

