from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, cast

from flask import g
from sqlalchemy import desc, func, select, text

from auth import ROLE_SUPER_ADMIN, normalize_role
from database import get_db_session
from models import Company, SupportTicket, User
from notifications import get_last_email_error, send_support_email


CATEGORIES = {
    "Agent Issue",
    "Device Offline",
    "Login Tracking Issue",
    "Application Monitoring Issue",
    "Performance Issue",
    "Account Issue",
    "Other",
}
PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
STATUSES = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _user_company_id(user: User) -> Optional[int]:
    value = cast(Any, getattr(user, "company_id", None))
    return int(value) if value not in (None, "") else None


def _is_super_admin(user: User) -> bool:
    return normalize_role(user.role) == ROLE_SUPER_ADMIN


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


def _ticket_number(session) -> str:
    next_id = session.execute(select(func.nextval("support_ticket_number_seq"))).scalar_one()
    return f"AS-{datetime.now(timezone.utc):%Y%m%d}-{int(next_id):05d}"


def ensure_support_schema() -> None:
    with get_db_session() as session:
        session.execute(func.to_regclass("support_ticket_number_seq"))
        session.execute(text("CREATE SEQUENCE IF NOT EXISTS support_ticket_number_seq START 1"))


def serialize_ticket(ticket: SupportTicket) -> Dict[str, Any]:
    company = getattr(ticket, "company", None)
    created_by = getattr(ticket, "created_by", None)
    return {
        "id": int(cast(Any, ticket.id)),
        "ticketNumber": ticket.ticket_number,
        "companyId": int(cast(Any, ticket.company_id)) if ticket.company_id else None,
        "companyName": company.name if company else None,
        "createdByUserId": int(cast(Any, ticket.created_by_user_id)) if ticket.created_by_user_id else None,
        "createdBy": created_by.display_name or created_by.email if created_by else None,
        "title": ticket.title,
        "category": ticket.category,
        "priority": ticket.priority,
        "description": ticket.description,
        "relatedDevice": ticket.related_device,
        "status": ticket.status,
        "adminResponse": ticket.admin_response,
        "createdAt": _iso(ticket.created_at),
        "updatedAt": _iso(ticket.updated_at),
        "resolvedAt": _iso(ticket.resolved_at),
    }


def list_support_tickets() -> Tuple[Dict[str, Any], int]:
    current_user = g.current_user
    company_id = _user_company_id(current_user)
    with get_db_session() as session:
        query = select(SupportTicket).order_by(desc(SupportTicket.created_at))
        if not _is_super_admin(current_user):
            query = query.where(SupportTicket.company_id == company_id)
        tickets = session.execute(query).scalars().all()
        for ticket in tickets:
            if ticket.company:
                ticket.company.name
            if ticket.created_by:
                ticket.created_by.email
        return {"tickets": [serialize_ticket(ticket) for ticket in tickets]}, 200


def create_support_ticket(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    current_user = g.current_user
    title = _clean(payload.get("title"))
    category = _clean(payload.get("category")) or "Other"
    priority = (_clean(payload.get("priority")) or "MEDIUM").upper()
    description = _clean(payload.get("description"))
    related_device = _clean(payload.get("relatedDevice") or payload.get("related_device")) or None

    if not title:
        return {"error": "Ticket title is required.", "field": "title"}, 400
    if category not in CATEGORIES:
        return {"error": "Invalid support category.", "field": "category"}, 400
    if priority not in PRIORITIES:
        return {"error": "Invalid priority.", "field": "priority"}, 400
    if not description:
        return {"error": "Ticket description is required.", "field": "description"}, 400

    with get_db_session() as session:
        session.execute(text("CREATE SEQUENCE IF NOT EXISTS support_ticket_number_seq START 1"))
        ticket = SupportTicket(
            ticket_number=_ticket_number(session),
            company_id=_user_company_id(current_user),
            created_by_user_id=int(cast(Any, current_user.id)),
            title=title,
            category=category,
            priority=priority,
            description=description,
            related_device=related_device,
            status="OPEN",
        )
        session.add(ticket)
        session.flush()
        if ticket.company:
            ticket.company.name
        if ticket.created_by:
            ticket.created_by.email
        return {"ticket": serialize_ticket(ticket), "message": "Support ticket created."}, 201


def update_support_ticket(ticket_id: int, payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    current_user = g.current_user
    if not _is_super_admin(current_user):
        return {"error": "Only SUPER_ADMIN can update support tickets."}, 403

    with get_db_session() as session:
        ticket = session.get(SupportTicket, ticket_id)
        if not ticket:
            return {"error": "Support ticket not found."}, 404
        status = _clean(payload.get("status")).upper()
        if status:
            if status not in STATUSES:
                return {"error": "Invalid ticket status.", "field": "status"}, 400
            ticket.status = status
            if status in {"RESOLVED", "CLOSED"} and not ticket.resolved_at:
                ticket.resolved_at = datetime.now(timezone.utc)
        if "adminResponse" in payload or "admin_response" in payload:
            ticket.admin_response = _clean(payload.get("adminResponse") or payload.get("admin_response")) or None
        ticket.updated_at = datetime.now(timezone.utc)
        if ticket.company:
            ticket.company.name
        if ticket.created_by:
            ticket.created_by.email
        return {"ticket": serialize_ticket(ticket), "message": "Support ticket updated."}, 200


def send_support_message(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    current_user = g.current_user
    subject = _clean(payload.get("subject"))
    priority = (_clean(payload.get("priority")) or "MEDIUM").upper()
    message = _clean(payload.get("message"))
    if not subject:
        return {"error": "Subject is required.", "field": "subject"}, 400
    if priority not in PRIORITIES:
        return {"error": "Invalid priority.", "field": "priority"}, 400
    if not message:
        return {"error": "Message is required.", "field": "message"}, 400

    company_name = None
    with get_db_session() as session:
        company_id = _user_company_id(current_user)
        company = session.get(Company, company_id) if company_id else None
        company_name = company.name if company else None

    sent = send_support_email(
        f"Asset Sentinel Support Request - {subject}",
        {
            "Subject": subject,
            "Priority": priority,
            "Message": message,
            "Company": company_name or "Platform / Unassigned",
            "User": current_user.email,
            "Role": normalize_role(current_user.role),
            "Timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not sent:
        return {"error": "Support email could not be sent.", "detail": get_last_email_error()}, 502
    return {"ok": True, "message": "Support email sent."}, 200
