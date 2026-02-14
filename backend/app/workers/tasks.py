from app.workers.celery_app import celery_app
from app.core.config import settings
from app.integration.email import send_email_smtp

from app.workers.celery_app import celery_app
from datetime import datetime

@celery_app.task(
    name="app.workers.tasks.send_booking_email",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)


@celery_app.task
def ping_task():
    print("✅ CELERY PING OK:", datetime.now())
    return "pong"

@celery_app.task
def send_booking_email(to_email: str, subject: str, body: str):
    send_email_smtp(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASS,
        to_email=to_email,
        subject=subject,
        body=body,
    )

