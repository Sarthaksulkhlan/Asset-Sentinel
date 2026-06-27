import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from auth import ROLE_ADMIN, hash_password
from database import get_db_session
from models import AdminUser, EarlyAccessRequest, User
from notifications import get_last_email_error, send_alert_email


EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
MOBILE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{4,64}$")
ALLOWED_PERSONAL_DOMAINS = {"gmail.com", "outlook.com", "yahoo.com", "icloud.com"}
BLOCKED_EMAIL_DOMAINS = {"example.com", "test.com", "invalid", "localhost"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _client_ip(request) -> Optional[str]:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None
    return request.remote_addr


def _password_errors(password: str) -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must include an uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must include a lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must include a number.")
    if not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must include a symbol.")
    return errors


def _error(message: str, field: Optional[str] = None, status: int = 400) -> Tuple[Dict[str, Any], int]:
    payload: Dict[str, Any] = {"error": message}
    if field:
        payload["field"] = field
    return payload, status


def _email_validation_error(email: str) -> Optional[str]:
    if not EMAIL_RE.match(email):
        return "Enter a valid email address."
    local, domain = email.rsplit("@", 1)
    domain = domain.lower().strip(".")
    labels = domain.split(".")
    if domain in BLOCKED_EMAIL_DOMAINS or labels[-1] in {"invalid", "localhost"}:
        return "Use a real personal or business email domain."
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return "Enter a valid email address."
    if any(not label or label.startswith("-") or label.endswith("-") for label in labels):
        return "Enter a valid email domain."
    if any(label.isdigit() for label in labels):
        return "Email domain cannot contain numeric-only labels."
    second_level = labels[-2] if len(labels) >= 2 else ""
    if domain not in ALLOWED_PERSONAL_DOMAINS and (len(second_level) < 4 or second_level[0].isdigit()):
        return "Use a legitimate personal or business email domain."
    return None


def _email_failure_response(message: str) -> Tuple[Dict[str, Any], int]:
    return {
        "ok": True,
        "message": message,
        "emailNotificationSent": False,
    }, 202


def submit_early_access(payload: Dict[str, Any], request) -> Tuple[Dict[str, Any], int]:
    full_name = _clean(payload.get("fullName") or payload.get("full_name"))
    email = _clean(payload.get("email") or payload.get("businessEmail") or payload.get("business_email")).lower()
    company = _clean(payload.get("company") or payload.get("companyName") or payload.get("company_name"))

    if not email:
        return _error("Email is required.", "email")
    email_error = _email_validation_error(email)
    if email_error:
        return _error(email_error, "email")

    ip_address = _client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    try:
        with get_db_session() as session:
            existing = session.execute(
                select(EarlyAccessRequest.id)
                .where(func.lower(EarlyAccessRequest.email) == email)
                .limit(1)
            ).scalar_one_or_none()
            if existing:
                return _error("This email is already on the early access list.", "email", 409)
            session.add(
                EarlyAccessRequest(
                    full_name=full_name or None,
                    email=email,
                    company=company or None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
    except IntegrityError:
        return _error("This email is already on the early access list.", "email", 409)

    sent = send_alert_email(
        "New Early Access Request - Asset Sentinel",
        {
            "Full Name": full_name,
            "Company": company,
            "Job Title": "",
            "Business Email": email,
            "Mobile Number": "",
            "Country": "",
            "Company Size": "",
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "IP Address": ip_address,
            "Browser/User Agent": user_agent,
        },
    )
    if not sent:
        detail = get_last_email_error()
        message = "Early access request saved, but the email notification could not be sent."
        if detail:
            message = f"{message} SMTP detail: {detail}."
        return _email_failure_response(
            message
        )
    return {"ok": True, "message": "Early access request received.", "emailNotificationSent": True}, 201


def register_admin(payload: Dict[str, Any], request) -> Tuple[Dict[str, Any], int]:
    required_fields = {
        "companyName": "Company Name",
        "industry": "Industry",
        "companySize": "Company Size",
        "country": "Country",
        "fullName": "Full Name",
        "workEmail": "Work Email",
        "mobileNumber": "Mobile Number",
        "jobTitle": "Job Title / Designation",
        "department": "Department",
        "username": "Username",
        "password": "Password",
        "confirmPassword": "Confirm Password",
    }
    values = {field: _clean(payload.get(field)) for field in required_fields}
    company_website = _clean(payload.get("companyWebsite"))

    for field, label in required_fields.items():
        if not values[field]:
            return _error(f"{label} is required.", field)

    email = values["workEmail"].lower()
    username = values["username"].lower()
    mobile_number = values["mobileNumber"]
    password = values["password"]

    email_error = _email_validation_error(email)
    if email_error:
        return _error(email_error, "workEmail")
    if not USERNAME_RE.match(username):
        return _error("Username must be 4-64 characters and use letters, numbers, dots, underscores, or hyphens.", "username")
    if not MOBILE_RE.match(mobile_number):
        return _error("Mobile number must include country code, for example +14155552671.", "mobileNumber")
    password_errors = _password_errors(password)
    if password_errors:
        return _error(password_errors[0], "password")
    if password != values["confirmPassword"]:
        return _error("Confirm password must match password.", "confirmPassword")
    if not bool(payload.get("termsAccepted")):
        return _error("Terms of Service agreement is required.", "termsAccepted")
    if not bool(payload.get("privacyAccepted")):
        return _error("Privacy Policy agreement is required.", "privacyAccepted")

    password_hash = hash_password(password)
    ip_address = _client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    try:
        with get_db_session() as session:
            existing_user = session.execute(
                select(User.id)
                .where(or_(func.lower(User.username) == username, func.lower(User.email) == email))
                .limit(1)
            ).scalar_one_or_none()
            existing_registration = session.execute(
                select(AdminUser.id)
                .where(or_(func.lower(AdminUser.username) == username, func.lower(AdminUser.work_email) == email))
                .limit(1)
            ).scalar_one_or_none()
            if existing_user or existing_registration:
                field = "username" if existing_user else "workEmail"
                return _error("Username or email is already registered.", field, 409)

            session.add(
                AdminUser(
                    company_name=values["companyName"],
                    company_website=company_website or None,
                    industry=values["industry"],
                    company_size=values["companySize"],
                    country=values["country"],
                    full_name=values["fullName"],
                    work_email=email,
                    mobile_number=mobile_number,
                    job_title=values["jobTitle"],
                    department=values["department"],
                    username=username,
                    password_hash=password_hash,
                    terms_accepted=True,
                    privacy_accepted=True,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
            )
            session.add(
                User(
                    username=username,
                    email=email,
                    display_name=values["fullName"],
                    password_hash=password_hash,
                    role=ROLE_ADMIN,
                    is_active=True,
                    external_provider="local",
                    external_subject=username,
                )
            )
    except IntegrityError:
        return _error("Username or email is already registered.", "username", 409)

    sent = send_alert_email(
        "New Admin Registration - Asset Sentinel",
        {
            "Full Name": values["fullName"],
            "Company": values["companyName"],
            "Job Title": values["jobTitle"],
            "Business Email": email,
            "Mobile Number": mobile_number,
            "Country": values["country"],
            "Company Size": values["companySize"],
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "IP Address": ip_address,
            "Browser/User Agent": user_agent,
            "Company Website": company_website,
            "Industry": values["industry"],
            "Department": values["department"],
            "Username": username,
        },
    )
    if not sent:
        return _email_failure_response(
            "Registration saved, but the email notification could not be sent. Please check SMTP configuration."
        )
    return {"ok": True, "message": "Enterprise registration completed.", "emailNotificationSent": True}, 201
