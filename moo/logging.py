import logging
import re

from celery._state import get_current_task
from celery.app.log import TaskFormatter
from celery.utils.log import ColorFormatter


class CeleryTaskFilter(logging.Filter):
    def filter(self, record):
        return record.processName.find("Worker") != -1


class CeleryProcessFilter(logging.Filter):
    def filter(self, record):
        return record.processName == "MainProcess"


class NotCeleryFilter(logging.Filter):
    def filter(self, record):
        return record.processName != "MainProcess" and record.processName.find("Worker") == -1


_TASK_REF_RE = re.compile(r"Task ([\w.]+)\[([0-9a-f-]+)\]")
_TASK_REF_STRIP_RE = re.compile(r"Task [\w.]+\[[0-9a-f-]+\] ")
_DURATION_RE = re.compile(r"(?<=in )(\d+\.\d{4,})(?=s\b)")


def _short_name(name):
    return name.rsplit(".", 1)[-1]


def _short_id(tid):
    return tid.split("-", 1)[0]


def _compress_task_ref(match):
    return f"Task {_short_name(match.group(1))}[{_short_id(match.group(2))}]"


def _round_duration(match):
    return f"{float(match.group(1)):.3f}"


class ShortTaskFormatter(TaskFormatter):
    """Worker-side: shortens prefix task_name/task_id and strips the redundant
    'Task X[Y] ' that celery.app.trace duplicates inside the message body."""

    def format(self, record):
        task = get_current_task()
        if task and task.request:
            record.__dict__.update(
                task_id=_short_id(task.request.id),
                task_name=_short_name(task.name),
            )
        else:
            record.__dict__.setdefault("task_name", "???")
            record.__dict__.setdefault("task_id", "???")
        # Skip TaskFormatter.format — it would overwrite our shortened values
        # with the full task.name / task.request.id from the current task.
        s = ColorFormatter.format(self, record)
        s = _TASK_REF_STRIP_RE.sub("", s, count=1)
        s = _DURATION_RE.sub(_round_duration, s)
        return s


class ShortProcessFormatter(ColorFormatter):
    """MainProcess: no prefix, so shorten the embedded task reference in place."""

    def format(self, record):
        s = super().format(record)
        s = _TASK_REF_RE.sub(_compress_task_ref, s)
        s = _DURATION_RE.sub(_round_duration, s)
        return s
