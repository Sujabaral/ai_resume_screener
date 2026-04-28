import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
HR_NAME = os.getenv("HR_NAME", "HR Team")


def send_email(to_email, subject, body):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        return False, "Email credentials missing. Check .env EMAIL_USER and EMAIL_PASSWORD."

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to_email

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, [to_email], msg.as_string())

        return True, "Email sent successfully"

    except smtplib.SMTPAuthenticationError:
        return False, "Gmail login failed. Use a valid Gmail App Password, not your normal Gmail password."

    except smtplib.SMTPRecipientsRefused:
        return False, f"Recipient email was refused: {to_email}"

    except smtplib.SMTPConnectError:
        return False, "Could not connect to Gmail SMTP server."

    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"

    except Exception as e:
        return False, f"Unexpected email error: {str(e)}"


def acceptance_template(candidate_name, job_title):
    return f"""
Dear {candidate_name},

Congratulations. Based on your application for the {job_title} position, you have been shortlisted for the next stage of our hiring process.

Our team will contact you soon with further details.

Best regards,
{HR_NAME}
MIDAS HEALTH SERVICES
"""


def rejection_template(candidate_name, job_title):
    return f"""
Dear {candidate_name},

Thank you for applying for the {job_title} position.

After reviewing your application, we regret to inform you that you have not been shortlisted for this role at this time.

We appreciate your interest and wish you the best in your future applications.

Best regards,
{HR_NAME}
MIDAS HEALTH SERVICES
"""