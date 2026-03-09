# -*- coding: utf-8 -*-
"""
Celery Tasks for executing commands or raw Python code.
"""

import logging
import warnings
from typing import Any, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import transaction

from moo.core.models import verb

from . import code, exceptions, parse
from .models import Object, Verb

log = get_task_logger(__name__)
background_log = logging.getLogger(f"{__name__}.background")


@shared_task(bind=True)
def parse_command(self, caller_id: int, line: str) -> list[Any]:
    """
    Parse a command-line and invoke the requested verb.

    :param caller_id: the PK of the caller of this command
    :param line: the natural-language command to parse and execute
    :return: a list of output lines
    :raises UserError: if a verb failure happens
    """
    output = []
    task_id = self.request.id
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        with code.ContextManager(caller, output.append, task_id=task_id) as ctx:
            try:
                log.info(f"{caller}: {line}")
                parse.interpret(ctx, line)
            except exceptions.UserError as e:
                log.error(f"{caller}: {e}")
                output.append(f"[bold red]{e}[/bold red]")
    return output


@shared_task(bind=True)
def parse_code(self, caller_id: int, source: str, runtype: str = "exec") -> list[list[Any], Any]:
    """
    Execute code in a task.

    :param caller_id: the PK of the caller of this command
    :param source: the Python code to execute
    :return: a list of output lines and the result value, if any
    """
    output = []
    task_id = self.request.id
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        with code.ContextManager(caller, output.append, task_id=task_id):
            result = code.interpret(source, "__main__", runtype=runtype)
    return output, result


@shared_task(bind=True)
def invoke_verb(
    self, *args, caller_id: int = None, player_id: Optional[int] = None, this_id: int = None, verb_name: int = None, callback_this_id: Optional[int] = None, callback_verb_name: Optional[int] = None, **kwargs
) -> None:
    """
    Asynchronously execute a Verb, optionally returning the result to another Verb.
    The `print()` method logs to a `moo.core.tasks.background` instead of sending
    to the caller; this could probably be improved.

    :param caller_id: the PK of the verb owner (for permission checks)
    :param player_id: the PK of the triggering player (for context.player); defaults to caller_id
    :param verb_id: the PK of the Verb to execute
    :param callback_verb_id: the PK of the verb to send the result to
    """
    from moo.core import context

    task_id = self.request.id
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        player = Object.objects.get(pk=player_id) if player_id else caller
        this = Object.objects.get(pk=this_id)
        verb = this.get_verb(verb_name)
        with code.ContextManager(caller, background_log.info, task_id=task_id, player=player):
            result = verb(*args, **kwargs)
            if callback_verb_name and callback_this_id:
                invoke_verb.delay(result, caller_id=caller_id, this_id=callback_this_id, verb_name=callback_verb_name)
