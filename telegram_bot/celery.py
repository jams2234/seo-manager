"""
Celery configuration for telegram_bot project.
"""
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegram_bot.settings')

app = Celery('telegram_bot')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Worker pool configuration for stability with Google API clients
# The prefork pool can cause SIGABRT crashes with C libraries (SSL/grpc)
# Using 'solo' pool for single-task processing avoids these issues
app.conf.update(
    worker_pool='solo',           # Single process pool (no fork issues)
    worker_concurrency=1,         # One task at a time (parallelism in ThreadPoolExecutor)
    worker_prefetch_multiplier=1, # Don't prefetch tasks
    task_acks_late=True,          # Acknowledge after completion
    task_reject_on_worker_lost=True,  # Retry if worker crashes
)

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
