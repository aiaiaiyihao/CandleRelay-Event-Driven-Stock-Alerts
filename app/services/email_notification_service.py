import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import (
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_TLS,
)
from app.models.Alert import Alert
from app.models.Rule import Rule
from app.models.User import User


def send_alert_emails(alerts: list[Alert], session: Session) -> int:
    if not alerts or not SMTP_HOST or not SMTP_FROM_EMAIL:
        return 0
    sent = 0
    for alert in alerts:
        recipient = session.execute(
            select(User.identifier)
            .join(Rule, Rule.user_id == User.id)
            .where(Rule.id == alert.rule_id, User.identifier_type == "email")
        ).scalar_one_or_none()
        if recipient is None:
            continue
        message = EmailMessage()
        message["Subject"] = f"CandleRelay alert: {alert.symbol}"
        message["From"] = SMTP_FROM_EMAIL
        message["To"] = recipient
        message.set_content(
            f"Your {alert.symbol} alert was triggered at "
            f"{alert.market_timestamp.isoformat()} ({alert.timeframe}).\n\n"
            "Open CandleRelay to review the evaluated conditions."
        )
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as client:
                if SMTP_USE_TLS:
                    client.starttls()
                if SMTP_USERNAME:
                    client.login(SMTP_USERNAME, SMTP_PASSWORD)
                client.send_message(message)
            sent += 1
        except (OSError, smtplib.SMTPException):
            logging.exception("Unable to email alert %s", alert.id)
    return sent
