import smtplib
from email.message import EmailMessage

from mail_agent.config import Settings
from mail_agent.contracts import RouteRequest, SendEmailArgs


def deliver(settings: Settings, request: RouteRequest, recipient: str, request_id: str) -> dict:
    recipient = SendEmailArgs(recipient=recipient).recipient
    message = EmailMessage()
    message["From"] = "router@example.com"
    message["To"] = recipient
    message["Reply-To"] = str(request.email)
    message["Subject"] = f"Zgłoszenie {request_id}"
    message["Message-ID"] = f"<{request_id}@mail-agent.example.com>"
    message["X-Request-ID"] = request_id
    message.set_content(request.message)
    # Bez ponowień: po zerwaniu połączenia przyjęcie maila może być niejednoznaczne.
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout
    ) as smtp:
        refused = smtp.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
    return {"status": "smtp_accepted", "recipient": recipient}
