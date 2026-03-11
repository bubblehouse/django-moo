# -*- coding: utf-8 -*-
"""
Celery workers run the verb tasks.
"""

from pathlib import Path

from celery import Celery, bootsteps
from celery.signals import setup_logging, beat_init, worker_ready, worker_shutdown, worker_process_init
from kombu.serialization import register

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from . import celeryconfig
from .core import moojson

WORKER_READINESS_FILE = Path('/tmp/worker-readiness')
WORKER_LIVENESS_FILE = Path('/tmp/worker-liveness')
BEAT_READINESS_FILE = Path('/tmp/beat-readiness')
BEAT_LIVENESS_FILE = Path('/tmp/beat-liveness.pid')

app = Celery("moo")
app.config_from_object("moo.celeryconfig")
app.autodiscover_tasks()

register("moojson", moojson.dumps, moojson.loads, content_type="application/x-moojson", content_encoding="utf-8")

@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    provider = TracerProvider(resource=Resource.create())
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    CeleryInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()

@setup_logging.connect
def configure_celery_logging(**kwargs):
    from logging.config import dictConfig

    dictConfig(celeryconfig.logging)

@beat_init.connect
def beat_ready(**kwargs):
    BEAT_READINESS_FILE.touch()

@worker_ready.connect
def worker_ready(**kwargs):
    WORKER_READINESS_FILE.touch()

@worker_shutdown.connect
def worker_shutdown(**kwargs):
    WORKER_READINESS_FILE.unlink(missing_ok=True)

@app.steps["worker"].add
class LivenessProbe(bootsteps.StartStopStep):
    requires = {'celery.worker.components:Timer'}

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.requests = []
        self.tref = None

    def start(self, parent):
        self.tref = parent.timer.call_repeatedly(
            1.0, self.update_heartbeat_file, (parent,), priority=10,
        )

    def stop(self, parent):
        WORKER_LIVENESS_FILE.unlink(missing_ok=True)

    def update_heartbeat_file(self, worker):
        WORKER_LIVENESS_FILE.touch()
