
import aiosmtplib

from email.message import EmailMessage

from app.core.config import settings


class AlertEmail:

    def __init__(
        self,
        title: str,
        body: str,
        url: str | None = None,
        action_text: str | None = None,
    ):
        self.title = title
        self.body = body
        self.url = url
        self.action_text = action_text or "View Details"

    async def send(self, recipient: str):

        message = EmailMessage()

        message["Subject"] = self.title
        message["From"] = settings.MAIL_FROM
        message["To"] = recipient

        lines = [
            line
            for line in self.body.splitlines()
            if line.strip()
        ]

        content = "\n\n".join(lines)

        if self.url:
            content += (
                f"\n\n{self.action_text}: {self.url}"
            )

        message.set_content(content)

        await aiosmtplib.send(
            message,
            hostname=settings.MAIL_HOST,
            port=settings.MAIL_PORT,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            use_tls=True,
        )
