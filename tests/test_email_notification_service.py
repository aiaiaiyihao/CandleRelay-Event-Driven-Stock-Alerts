from unittest.mock import MagicMock, patch

from app.services.email_notification_service import send_alert_emails


def test_email_delivery_is_disabled_without_smtp_configuration():
    assert send_alert_emails([MagicMock()], MagicMock()) == 0


def test_email_delivery_uses_rule_owner_email():
    alert = MagicMock(
        id="alert-1",
        rule_id="rule-1",
        symbol="NVDA",
        timeframe="1m",
    )
    alert.market_timestamp.isoformat.return_value = "2026-08-11T18:05:00+00:00"
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = "owner@example.com"
    smtp = MagicMock()
    with (
        patch("app.services.email_notification_service.SMTP_HOST", "smtp.example.com"),
        patch("app.services.email_notification_service.SMTP_FROM_EMAIL", "alerts@example.com"),
        patch("app.services.email_notification_service.smtplib.SMTP", return_value=smtp),
    ):
        smtp.__enter__.return_value = smtp
        count = send_alert_emails([alert], session)

    assert count == 1
    smtp.send_message.assert_called_once()
