import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import or_, select, text

from database import get_db_session
from models import Asset, DevicePairingCode, User
from storage import resolve_device_uid


PAIRING_CODE_LIFETIME = timedelta(hours=20)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(code: DevicePairingCode) -> Dict[str, Any]:
    return {
        "code": code.code,
        "createdAt": code.created_at.isoformat() if code.created_at else None,
        "expiresAt": code.expires_at.isoformat(),
        "used": bool(code.used),
    }


def issue_pairing_code(user_id: int) -> Dict[str, Any]:
    now = _utcnow()
    with get_db_session() as session:
        session.execute(text("SELECT pg_advisory_xact_lock(827364910)"))
        active = session.execute(
            select(DevicePairingCode)
            .where(DevicePairingCode.user_id == user_id)
            .where(DevicePairingCode.used.is_(False))
            .where(DevicePairingCode.expires_at > now)
            .order_by(DevicePairingCode.created_at.desc(), DevicePairingCode.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if active:
            return _serialize(active)

        for _ in range(100):
            value = f"{secrets.randbelow(10000):04d}"
            collision = session.execute(
                select(DevicePairingCode.id)
                .where(DevicePairingCode.code == value)
                .where(DevicePairingCode.used.is_(False))
                .where(DevicePairingCode.expires_at > now)
                .limit(1)
            ).scalar_one_or_none()
            if collision is None:
                code = DevicePairingCode(
                    user_id=user_id,
                    code=value,
                    expires_at=now + PAIRING_CODE_LIFETIME,
                    used=False,
                )
                session.add(code)
                session.flush()
                return _serialize(code)
        raise RuntimeError("Unable to allocate a unique pairing code")


def get_pairing_code(user_id: int) -> Dict[str, Any]:
    return issue_pairing_code(user_id)


def _find_device(session, payload: Dict[str, Any]) -> Optional[Asset]:
    device_uid = resolve_device_uid(payload)
    conditions = [Asset.device_uid == device_uid]
    if payload.get("hostname"):
        conditions.append(Asset.hostname == payload["hostname"])
    if payload.get("uuid"):
        conditions.append(Asset.uuid == payload["uuid"])
    if payload.get("bios_serial"):
        conditions.append(Asset.bios_serial == payload["bios_serial"])
    if payload.get("baseboard_serial"):
        conditions.append(Asset.baseboard_serial == payload["baseboard_serial"])
    if payload.get("mac_address"):
        conditions.append(Asset.mac_address == payload["mac_address"])
    return session.execute(
        select(Asset).where(or_(*conditions)).order_by(Asset.id.desc()).limit(1)
    ).scalar_one_or_none()


def pairing_status(payload: Dict[str, Any]) -> Dict[str, Any]:
    with get_db_session() as session:
        asset = _find_device(session, payload)
        return {
            "paired": bool(asset),
            "deviceUid": asset.device_uid if asset else resolve_device_uid(payload),
        }


def pair_device(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    code_value = str(payload.get("otp") or "").strip()
    if len(code_value) != 4 or not code_value.isdigit():
        return {"error": "Invalid or Expired Pairing Code."}, 400

    now = _utcnow()
    with get_db_session() as session:
        code = session.execute(
            select(DevicePairingCode)
            .where(DevicePairingCode.code == code_value)
            .where(DevicePairingCode.used.is_(False))
            .where(DevicePairingCode.expires_at > now)
            .with_for_update()
            .limit(1)
        ).scalar_one_or_none()
        if not code:
            return {"error": "Invalid or Expired Pairing Code."}, 400
        user = session.get(User, code.user_id)
        if not user or not user.is_active or not user.company_id:
            return {"error": "Invalid or Expired Pairing Code."}, 400

        device_record = {
            "hostname": payload.get("hostname") or "Unknown",
            "uuid": payload.get("uuid"),
            "bios_serial": payload.get("bios_serial"),
            "baseboard_serial": payload.get("baseboard_serial"),
            "mac_address": payload.get("mac_address"),
            "composite_id": payload.get("composite_id"),
            "company_id": user.company_id,
            "collection_method": payload.get("collection_method") or "none",
            "collection_errors": [],
            "collected_at": now.isoformat(),
        }
        device_uid = resolve_device_uid(device_record)
        asset = _find_device(session, device_record)
        if asset and asset.owner_user_id not in {None, user.id}:
            return {"error": "This device is already paired to another account."}, 409
        if not asset:
            raw_uuid = device_record.get("uuid")
            try:
                parsed_uuid = UUID(str(raw_uuid)) if raw_uuid else None
            except ValueError:
                parsed_uuid = None
            asset = Asset(
                company_id=user.company_id,
                owner_user_id=user.id,
                device_uid=device_uid,
                hostname=device_record["hostname"],
                mac_address=device_record.get("mac_address"),
                bios_serial=device_record.get("bios_serial"),
                baseboard_serial=device_record.get("baseboard_serial"),
                uuid=parsed_uuid,
                composite_id=device_record.get("composite_id"),
                status="Offline",
                collection_method=device_record["collection_method"],
                collection_errors=[],
                collected_at=now,
            )
            session.add(asset)
        asset.company_id = user.company_id
        asset.owner_user_id = user.id
        code.used = True
        code.used_at = now
        code.paired_device_uid = device_uid
        return {"ok": True, "paired": True, "deviceUid": device_uid}, 200
