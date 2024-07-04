# -*- coding: utf-8 -*-
"""
Celery Tasks for executing commands or raw Python code.
"""

import logging
from typing import Any

from django.db import transaction
from celery import shared_task

from . import code, parse, exceptions
from .models import Object

log = logging.getLogger(__name__)

@shared_task
def parse_command(caller_id:int, line:str) -> list[Any]:
    """
    Parse a command-line and invoke the requested verb.

    :param caller_id: the PK of the caller of this command
    :param line: the natural-language command to parse and execute
    :return: a list of output lines
    :raises UserError: if a verb failure happens
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
def parse_code(caller_id:Object, source:str, runtype:str="exec") -> list[list[Any], Any]:
    """
    Execute code in a task.

    :param caller_id: the PK of the caller of this command
    :param source: the Python code to execute
    :return: a list of output lines and the result value, if any
    """
    output = []
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        with code.context(caller, output.append):
            result = code.interpret(source, runtype=runtype)
    return output, result
