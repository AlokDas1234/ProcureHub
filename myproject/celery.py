# myproject/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

# Create Celery app
app = Celery("myproject")

# Load config from Django settings, using CELERY_ prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks from all apps
app.autodiscover_tasks()

# Example Beat schedule
app.conf.beat_schedule = {
    "broadcast-auction-timer-every-second": {
        "task": "myapp.tasks.broadcast_remaining_time",
        "schedule": 1.0,  # run every 1 second
    },
}
