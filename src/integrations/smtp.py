# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""SMTP email integration provider."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Any

from src.integrations.base import EmailProvider
from src.integrations.registry import IntegrationRegistry


@IntegrationRegistry.register
class SmtpProvider(EmailProvider):
    """SMTP email sending integration."""

    @classmethod
    def get_type(cls) -> str:
        return "smtp"

    @classmethod
    def get_display_name(cls) -> str:
        return "SMTP Email"

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["host", "port", "from_email"],
            "properties": {
                "host": {
                    "type": "string",
                    "title": "SMTP Host",
                    "description": "SMTP server hostname",
                },
                "port": {
                    "type": "integer",
                    "title": "SMTP Port",
                    "description": "SMTP server port (usually 587 for TLS, 465 for SSL)",
                    "default": 587,
                },
                "username": {
                    "type": "string",
                    "title": "Username",
                    "description": "SMTP authentication username (optional)",
                },
                "password": {
                    "type": "string",
                    "title": "Password",
                    "description": "SMTP authentication password (optional)",
                    "format": "password",
                },
                "from_email": {
                    "type": "string",
                    "title": "From Email",
                    "description": "Sender email address",
                    "format": "email",
                },
                "from_name": {
                    "type": "string",
                    "title": "From Name",
                    "description": "Sender display name (optional)",
                },
                "use_tls": {
                    "type": "boolean",
                    "title": "Use TLS",
                    "description": "Use STARTTLS encryption",
                    "default": True,
                },
                "use_ssl": {
                    "type": "boolean",
                    "title": "Use SSL",
                    "description": "Use SSL encryption (overrides TLS if enabled)",
                    "default": False,
                },
            },
        }

    def __init__(self, config: dict[str, Any]):
        self.host = config["host"]
        self.port = config.get("port", 587)
        self.username = config.get("username")
        self.password = config.get("password")
        self.from_email = config["from_email"]
        self.from_name = config.get("from_name", "")
        self.use_tls = config.get("use_tls", True)
        self.use_ssl = config.get("use_ssl", False)

    async def health_check(self) -> tuple[bool, str]:
        """Check connectivity to SMTP server."""
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.use_tls:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)
            server.quit()
            return True, "Connected"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed"
        except smtplib.SMTPConnectError:
            return False, "Connection failed"
        except TimeoutError:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    async def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        body_html: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> bool:
        """
        Send email with optional HTML and attachments.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body: Email body (plain text)
            body_html: Email body (HTML, optional). If provided, creates multipart/alternative
            attachments: List of (filename, content, mime_type) tuples

        Returns:
            True if email was sent successfully
        """
        try:
            # Create the main message container
            msg = MIMEMultipart("mixed")

            # Set sender
            if self.from_name:
                msg["From"] = f"{self.from_name} <{self.from_email}>"
            else:
                msg["From"] = self.from_email

            msg["To"] = ", ".join(to)
            msg["Subject"] = subject

            # Create the body part
            if body_html:
                # Multipart/alternative for HTML + plain text
                alt_part = MIMEMultipart("alternative")
                alt_part.attach(MIMEText(body, "plain", "utf-8"))
                alt_part.attach(MIMEText(body_html, "html", "utf-8"))
                msg.attach(alt_part)
            else:
                # Plain text only
                msg.attach(MIMEText(body, "plain", "utf-8"))

            # Add attachments
            if attachments:
                for filename, content, mime_type in attachments:
                    part = MIMEBase(*mime_type.split("/", 1))
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={filename}",
                    )
                    msg.attach(part)

            # Send email
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=30)
                if self.use_tls:
                    server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(self.from_email, to, msg.as_string())
            server.quit()

            return True
        except Exception:
            return False
