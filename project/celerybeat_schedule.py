from celery.schedules import crontab
from datetime import timedelta

CELERY_IMPORTS = ("lib.tasks", "stats.tasks", "articles.tasks",)
CELERYBEAT_SCHEDULE = {
    'stats_inbox': {
        'task': 'stats.tasks.process_stats_inbox',
        'schedule': timedelta(seconds=30),
        'args': (),
    },
    'truncate_unique_ips': {
        'task': 'stats.tasks.truncate_unique_ip_lists',
        'schedule': crontab(minute=0, hour=0),
        'args': (),
    },
    'sitemaps': {
        'task': 'lib.tasks.refresh_sitemaps',
        'schedule': timedelta(minutes=30),
        'args': (),
    },
}