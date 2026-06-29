import smtplib
from email.message import EmailMessage
import logging
from typing import Any, Dict, Optional

from config import Config


logger = logging.getLogger("asset_sentinel.notifications")
_last_email_error = ""


def get_last_email_error() -> str:
    return _last_email_error


def _set_last_email_error(message: str) -> None:
    global _last_email_error
    _last_email_error = message


def _format_value(value: Any) -> str:
    if value in (None, ""):
        return "Not provided"
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            lines.append(f"  - {str(key).replace('_', ' ')}: {_format_value(item)}")
        return "\n" + "\n".join(lines)
    if isinstance(value, (list, tuple, set)):
        if not value:
            return "Not provided"
        return "\n" + "\n".join(f"  - {_format_value(item)}" for item in value)
    return str(value)


def _build_email_body(subject: str, fields: Dict[str, Any]) -> str:
    lines = [
        "Asset Sentinel Notification",
        "=" * 29,
        "",
        subject,
        "",
        "Submission Details",
        "-" * 18,
    ]
    for label, value in fields.items():
        formatted = _format_value(value)
        if formatted.startswith("\n"):
            lines.append(f"{label}:{formatted}")
        else:
            lines.append(f"{label}: {formatted}")
    lines.extend([
        "",
        "This message was generated automatically by Asset Sentinel.",
    ])
    return "\n".join(lines)


def send_alert_email(subject: str, fields: Dict[str, Any]) -> bool:
    _set_last_email_error("")
    Config.reload_local_env()
    missing = [
        name for name, value in {
            "SMTP_HOST": Config.SMTP_HOST,
            "SMTP_USERNAME": Config.SMTP_USERNAME,
            "SMTP_PASSWORD": Config.SMTP_PASSWORD,
            "ALERT_EMAIL": Config.ALERT_EMAIL,
        }.items()
        if not value
    ]
    if missing:
        error_message = (
            f"missing environment variable(s): {', '.join(missing)}. "
            "For Gmail, set SMTP_USERNAME to the Gmail address and SMTP_PASSWORD "
            "to a Gmail App Password in .env."
        )
        _set_last_email_error(error_message)
        logger.error("Email notification skipped: %s", error_message)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = Config.SMTP_FROM_EMAIL or Config.SMTP_USERNAME
    message["To"] = Config.ALERT_EMAIL
    message.set_content(_build_email_body(subject, fields))

    try:
        smtp_cls = smtplib.SMTP_SSL if Config.SMTP_USE_SSL else smtplib.SMTP
        with smtp_cls(Config.SMTP_HOST, Config.SMTP_PORT, timeout=20) as smtp:
            smtp.ehlo()
            if Config.SMTP_USE_TLS and not Config.SMTP_USE_SSL:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("Email notification sent to %s with subject %s", Config.ALERT_EMAIL, subject)
        return True
    except smtplib.SMTPAuthenticationError as exc:
        _set_last_email_error(f"SMTP authentication failed for {Config.SMTP_USERNAME} via {Config.SMTP_HOST}:{Config.SMTP_PORT}: {exc}")
        logger.exception("SMTP authentication failed for %s via %s:%s: %s", Config.SMTP_USERNAME, Config.SMTP_HOST, Config.SMTP_PORT, exc)
        return False
    except smtplib.SMTPException as exc:
        _set_last_email_error(f"SMTP send failed via {Config.SMTP_HOST}:{Config.SMTP_PORT} using tls={Config.SMTP_USE_TLS} ssl={Config.SMTP_USE_SSL}: {exc}")
        logger.exception("SMTP send failed via %s:%s using tls=%s ssl=%s: %s", Config.SMTP_HOST, Config.SMTP_PORT, Config.SMTP_USE_TLS, Config.SMTP_USE_SSL, exc)
        return False
    except Exception as exc:
        _set_last_email_error(f"Unexpected email failure via {Config.SMTP_HOST}:{Config.SMTP_PORT}: {exc}")
        logger.exception("Email notification failed unexpectedly for subject %s via %s:%s: %s", subject, Config.SMTP_HOST, Config.SMTP_PORT, exc)
        return False
