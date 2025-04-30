import os
import aiosmtplib
from email.message import EmailMessage

async def send_verification_email(to_email: str, code: str):
    msg = EmailMessage()
    msg['From'] = os.getenv("EMAIL_HOST_USER")
    msg['To'] = to_email
    msg['Subject'] = "Код подтверждения регистрации"
    msg.set_content(f"Ваш код подтверждения: {code}")

    await aiosmtplib.send(
        msg,
        hostname=os.getenv("EMAIL_HOST"),
        port=int(os.getenv("EMAIL_PORT")),
        username=os.getenv("EMAIL_HOST_USER"),
        password=os.getenv("EMAIL_HOST_PASSWORD"),
        start_tls=True
    )
