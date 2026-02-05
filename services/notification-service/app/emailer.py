import os
import smtplib
import logging
from email.mime.text import MIMEText

logger = logging.getLogger("notification-service.emailer")

SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))

# Optional (Mailhog doesn't need these)
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

FROM_EMAIL = os.environ.get("FROM_EMAIL") or SMTP_USER or "noreply@local"

# Default OFF for Mailhog
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() == "true"
SMTP_USE_AUTH = os.environ.get("SMTP_USE_AUTH", "false").lower() == "true"


def send_email(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEText(html_body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        # For Mailhog: no TLS, no auth
        if SMTP_USE_TLS:
            s.starttls()

        if SMTP_USE_AUTH:
            if not SMTP_USER or not SMTP_PASS:
                raise RuntimeError("SMTP_USE_AUTH=true but SMTP_USER/SMTP_PASS not set")
            s.login(SMTP_USER, SMTP_PASS)

        s.sendmail(FROM_EMAIL, [to_email], msg.as_string())

    logger.info("Email sent to %s subject=%s", to_email, subject)
