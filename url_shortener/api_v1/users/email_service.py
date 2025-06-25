import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os
from core.config import settings

SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USERNAME
SMTP_PASSWORD = settings.SMTP_PASSWORD
FROM_EMAIL = settings.FROM_EMAIL or settings.SMTP_USERNAME
API_URL = settings.API_URL

# Debug print
print(f"🔧 Email config loaded:")
print(f"   SMTP_HOST: {SMTP_HOST}")
print(f"   SMTP_PORT: {SMTP_PORT}")
print(f"   SMTP_USERNAME: {SMTP_USERNAME}")
print(f"   SMTP_PASSWORD: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'NOT SET'}")
print(f"   FROM_EMAIL: {FROM_EMAIL}")

def create_message(recipients: List[str], subject: str, body: str) -> MIMEMultipart:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = FROM_EMAIL
    message["To"] = ", ".join(recipients)
    
    html_part = MIMEText(body, "html", "utf-8")
    message.attach(html_part)
    
    return message

async def send_email(recipients: List[str], subject: str, body: str) -> bool:
    try:
        print(f"Attempting to send email to: {recipients}")
        print(f"SMTP: {SMTP_HOST}:{SMTP_PORT}")
        print(f"Username: {SMTP_USERNAME}")
        print(f"From: {FROM_EMAIL}")
        
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print("ERROR: SMTP credentials not configured!")
            return False
        
        message = create_message(recipients=recipients, subject=subject, body=body)
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
        )
        print("✅ Email sent successfully!")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


