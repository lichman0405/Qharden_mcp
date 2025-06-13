# This module initializes and configures the Celery application instance.
# Author: Shibo Li
# Date: 2025-06-13
# Version: 0.1.0

from celery import Celery
from app.core.config import get_settings

# Get the application settings
settings = get_settings()

# Initialize the Celery application
# The first argument 'mcp_tasks' is the name of the current module,
# which is conventional for Celery setup.
celery_app = Celery(
    'mcp_tasks',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks'] 
)

# Configure Celery settings
celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,  # Expire results after 1 hour
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Shanghai', 
    enable_utc=True,
)
