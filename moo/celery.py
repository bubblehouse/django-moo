from celery import Celery

app = Celery('moo')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
