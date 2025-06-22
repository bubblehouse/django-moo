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

from . import code, exceptions, parse
from .models import Object, Verb

log = get_task_logger(__name__)
background_log = logging.getLogger(f"{__name__}.background")


@shared_task
def parse_command(caller_id: int, line: str) -> list[Any]:
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
def parse_code(caller_id: int, source: str, runtype: str = "exec") -> list[list[Any], Any]:
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


@shared_task
def invoke_verb(
    *args, caller_id: int = None, verb_id: int = None, callback_verb_id: Optional[int] = None, **kwargs
) -> None:
    """
    Asynchronously execute a Verb, optionally returning the result to another Verb.
    The `print()` method logs to a `moo.core.tasks.background` instead of sending
    to the caller; this could probably be improved.

    :param caller_id: the PK of the caller of this command
    :param verb_id: the PK of the Verb to execute
    :param callback_verb_id: the PK of the verb to send the result to
    """
    from moo.core import api

    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        verb = Verb.objects.get(pk=verb_id)
        if "this_id" in kwargs:
            kwargs["this"] = Object.objects.get(pk=kwargs.pop("this_id"))
        else:
            warnings.warn(
                RuntimeWarning("invoke_verb: no this_id provided")
            )
        with code.context(caller, background_log.info):
            globals = code.get_default_globals()  # pylint: disable=redefined-builtin
            globals.update(code.get_restricted_environment(api.writer))
            result = code.r_exec(verb.code, {}, globals, *args, filename=repr(verb), **kwargs)
    if callback_verb_id:
        callback = Verb.objects.get(pk=callback_verb_id)
        invoked_name = callback.names.first().name
        invoke_verb.delay(invoked_name, result, caller_id=caller_id, verb_id=callback_verb_id)
