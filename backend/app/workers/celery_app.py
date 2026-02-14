from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "smartserve",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# timezone config (India)
celery_app.conf.timezone = "Asia/Kolkata"
celery_app.conf.enable_utc = False

# ✅ IMPORTANT: autodiscover tasks inside app.workers
celery_app.autodiscover_tasks(["app.workers"])
