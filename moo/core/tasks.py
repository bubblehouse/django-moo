import logging

from django.db import transaction
from celery import shared_task

from . import code, parse, exceptions
from .models import Object

log = logging.getLogger(__name__)

@shared_task
def parse_command(caller_id, line):
    """
    Execute a textual command in a task.
    """
    output = []
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        with code.context(caller, output.append):
            try:
                log.info(f"{caller}: {line}")
                parse.interpret(line)
            except exceptions.UserError as e:
                log.error(f"{caller}: {e}")
                output.append(f"[bold red]{e}[/bold red]")
    return output

@shared_task
def parse_code(caller_id, source, runtype="exec"):
    """
    Execute prompt code in a task.
    """
    output = []
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        with code.context(caller, output.append):
            result = code.interpret(source, runtype=runtype)
    return output, result
