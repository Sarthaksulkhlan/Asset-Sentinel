from typing import Any, Dict, Optional, cast

from sqlalchemy import desc, func, select

from database import get_db_session
from models import Alert, Asset, Company, SupportTicket, User
from support import serialize_ticket


def _count(session, query) -> int:
    return int(session.execute(query).scalar_one() or 0)


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _company_id(company: Company) -> int:
    return int(cast(Any, company.id))


def _company_stats(session, company_id: int) -> Dict[str, int]:
    total_devices = _count(session, select(func.count()).select_from(Asset).where(Asset.company_id == company_id))
    online_devices = _count(session, select(func.count()).select_from(Asset).where(Asset.company_id == company_id, Asset.status == "Online"))
    critical_alerts = _count(session, select(func.count()).select_from(Alert).where(Alert.company_id == company_id, Alert.severity == "CRITICAL"))
    return {
        "totalDevices": total_devices,
        "onlineDevices": online_devices,
        "offlineDevices": max(total_devices - online_devices, 0),
        "criticalAlerts": critical_alerts,
    }


def super_admin_overview() -> Dict[str, Any]:
    with get_db_session() as session:
        total_companies = _count(session, select(func.count()).select_from(Company))
        active_companies = _count(session, select(func.count()).select_from(Company).where(Company.status == "Active"))
        total_devices = _count(session, select(func.count()).select_from(Asset))
        online_devices = _count(session, select(func.count()).select_from(Asset).where(Asset.status == "Online"))
        offline_devices = _count(session, select(func.count()).select_from(Asset).where(Asset.status == "Offline"))
        critical_alerts = _count(session, select(func.count()).select_from(Alert).where(Alert.severity == "CRITICAL"))
        open_tickets = _count(session, select(func.count()).select_from(SupportTicket).where(SupportTicket.status.in_(["OPEN", "IN_PROGRESS"])))
        return {
            "totalCompanies": total_companies,
            "activeCompanies": active_companies,
            "totalDevices": total_devices,
            "onlineDevices": online_devices,
            "offlineDevices": offline_devices,
            "criticalAlerts": critical_alerts,
            "openSupportTickets": open_tickets,
            "platformHealth": "Operational" if critical_alerts == 0 else "Attention Required",
        }


def _admin_for_company(session, company_id: int) -> Optional[User]:
    return session.execute(
        select(User)
        .where(User.company_id == company_id)
        .where(User.role.in_(["COMPANY_ADMIN", "Admin"]))
        .order_by(User.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()


def serialize_company(session, company: Company) -> Dict[str, Any]:
    company_id = _company_id(company)
    admin = _admin_for_company(session, company_id)
    stats = _company_stats(session, company_id)
    return {
        "id": company_id,
        "name": company.name,
        "website": company.website,
        "industry": company.industry,
        "companySize": company.company_size,
        "country": company.country,
        "plan": company.plan,
        "status": company.status,
        "registrationDate": _iso(company.created_at),
        "companyAdmin": admin.display_name or admin.email if admin else None,
        "adminEmail": admin.email if admin else None,
        **stats,
    }


def list_companies() -> Dict[str, Any]:
    with get_db_session() as session:
        companies = session.execute(select(Company).order_by(desc(Company.created_at))).scalars().all()
        return {"companies": [serialize_company(session, company) for company in companies]}


def company_detail(company_id: int) -> tuple[Dict[str, Any], int]:
    with get_db_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return {"error": "Company not found."}, 404
        users = session.execute(select(User).where(User.company_id == company_id).order_by(User.created_at.asc())).scalars().all()
        assets = session.execute(select(Asset).where(Asset.company_id == company_id).order_by(Asset.hostname.asc()).limit(100)).scalars().all()
        alerts = session.execute(select(Alert).where(Alert.company_id == company_id).order_by(desc(Alert.timestamp)).limit(50)).scalars().all()
        tickets = session.execute(select(SupportTicket).where(SupportTicket.company_id == company_id).order_by(desc(SupportTicket.created_at)).limit(50)).scalars().all()
        for ticket in tickets:
            if ticket.company:
                ticket.company.name
            if ticket.created_by:
                ticket.created_by.email
        return {
            "company": serialize_company(session, company),
            "users": [
                {
                    "id": int(cast(Any, user.id)),
                    "email": user.email,
                    "username": user.username,
                    "displayName": user.display_name,
                    "role": user.role,
                    "isActive": user.is_active,
                    "createdAt": _iso(user.created_at),
                    "lastLoginAt": _iso(user.last_login_at),
                }
                for user in users
            ],
            "devices": [
                {
                    "hostname": asset.hostname,
                    "status": asset.status,
                    "lastSeen": _iso(asset.last_seen),
                    "cpuUsage": float(asset.cpu_usage_percent or 0),
                    "ramUsage": float(asset.ram_usage_percent or 0),
                }
                for asset in assets
            ],
            "alerts": [
                {
                    "alertType": alert.alert_type,
                    "hostname": alert.hostname,
                    "severity": alert.severity,
                    "timestamp": _iso(alert.timestamp),
                }
                for alert in alerts
            ],
            "tickets": [serialize_ticket(ticket) for ticket in tickets],
        }, 200


def update_company_status(company_id: int, status: str) -> tuple[Dict[str, Any], int]:
    normalized = "Active" if status.lower() == "active" else "Suspended" if status.lower() == "suspended" else ""
    if not normalized:
        return {"error": "Status must be Active or Suspended."}, 400
    with get_db_session() as session:
        company = session.get(Company, company_id)
        if not company:
            return {"error": "Company not found."}, 404
        company.status = normalized
        return {"company": serialize_company(session, company), "message": f"Company {normalized.lower()}."}, 200


def all_support_tickets() -> Dict[str, Any]:
    with get_db_session() as session:
        tickets = session.execute(select(SupportTicket).order_by(desc(SupportTicket.created_at))).scalars().all()
        for ticket in tickets:
            if ticket.company:
                ticket.company.name
            if ticket.created_by:
                ticket.created_by.email
        return {"tickets": [serialize_ticket(ticket) for ticket in tickets]}
