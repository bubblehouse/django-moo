# -*- coding: utf-8 -*-
"""
Celery Tasks for executing commands or raw Python code.
"""

import logging
from typing import Any, Optional

from django.db import transaction
from celery import shared_task

from . import code, parse, exceptions
from .models import Object, Verb

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
def parse_code(caller_id:int, source:str, runtype:str="exec") -> list[list[Any], Any]:
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
def invoke_verb(caller_id:int, verb_id:int, *args, callback_verb_id:Optional[int]=None, **kwargs) -> list[list[Any], Any]:
    """
    Asynchronously execute a Verb, optionally returning the result to another Verb.

    :param caller_id: the PK of the caller of this command
    :param verb_id: the PK of the Verb to execute
    :param callback_verb_id: the PK of the verb to send the result to
    :return: a list of output lines and the result value, if any
    """
    from moo.core import api
    output = []
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        verb = Verb.objects.get(pk=verb_id)
        with code.context(caller, output.append):
            globals = code.get_default_globals()  # pylint: disable=redefined-builtin
            globals.update(code.get_restricted_environment(api.writer))
            result = code.r_exec(verb.code, {}, globals, *args, filename=repr(verb), **kwargs)
    if callback_verb_id:
        callback_verb.delay(caller_id, callback_verb_id, output, result)

@shared_task
def callback_verb(caller_id:int, verb_id:int, output:list[Any], result:Any) -> None:
    """
    Return a result to a Verb.

    :param caller_id: the PK of the caller of this command
    :param verb_id: the PK of the Verb to execute
    :param output: a list of output lines
    :param result: the result value, if any
    """
    from moo.core import api
    output = []
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        callback = Verb.objects.get(pk=verb_id)
        with code.context(caller, output.append):
            globals = code.get_default_globals()  # pylint: disable=redefined-builtin
            globals.update(code.get_restricted_environment(api.writer))
            code.r_exec(callback.code, {}, globals, filename=repr(callback), output=output, result=result)
