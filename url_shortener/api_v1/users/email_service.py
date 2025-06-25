import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os
from core.config import Settings
from utils.template_loader import render_template, get_text_version

settings = Settings()

# Email configuration
SMTP_HOST = getattr(settings, 'SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = getattr(settings, 'SMTP_PORT', 587)
SMTP_USERNAME = getattr(settings, 'SMTP_USERNAME', 'SMTP')
SMTP_PASSWORD = getattr(settings, 'SMTP_PASSWORD', 'gxhqhhhqhtvsnrht')
FROM_EMAIL = getattr(settings, 'FROM_EMAIL', SMTP_USERNAME)
API_URL = getattr(settings, 'API_URL', 'http://localhost:8000')

async def send_email(
    to_emails: List[str],
    subject: str,
    html_content: str,
    text_content: str = None
) -> bool:
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = FROM_EMAIL
        message["To"] = ", ".join(to_emails)
        
        if text_content:
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)
        
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)
        
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    reset_url = f"{API_URL}/docs#/Users/reset_password_users_reset_password_post"
    
    subject = "Скидання пароля - URL Shortener"
    
    context = {
        "reset_url": reset_url,
        "reset_token": reset_token
    }
    
    try:
        html_content = render_template("password_reset.html", context)
        text_content = get_text_version(html_content)
        
        return await send_email([email], subject, html_content, text_content)
    except Exception as e:
        raise Exception(f"Error sending password reset email: {e}")
        


async def send_welcome_email(email: str, username: str) -> bool:
    subject = "Ласкаво просимо до URL Shortener!"
    
    context = {
        "username": username,
        "app_url": f"{API_URL}/docs"
    }
    
    try:
        html_content = render_template("welcome.html", context)
        text_content = get_text_version(html_content)
        
        return await send_email([email], subject, html_content, text_content)
    except Exception as e:
        raise Exception(f"Error sending password reset email: {e}")