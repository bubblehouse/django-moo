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
from .models import Object

log = get_task_logger(__name__)
background_log = logging.getLogger(f"{__name__}.background")


@shared_task(bind=True)
def parse_command(self, caller_id: int, line: str) -> tuple[list[Any], int]:
    """
    Parse a command-line and invoke the requested verb.

    :param caller_id: the PK of the caller of this command
    :param line: the natural-language command to parse and execute
    :return: ``(output, exit_status)`` — list of output lines and ``0`` on
        success, ``1`` if any caught exception fired.
    :raises UserError: if a verb failure happens
    """
    from django.core.cache import cache

    from moo.sdk import get_session_setting

    output: list[Any] = []
    exit_status = 0
    task_id = self.request.id
    caller = Object.objects.get(pk=caller_id)
    with code.ContextManager(caller, output.append, task_id=task_id, track_events=True) as ctx:
        prefix = "[ERROR] " if get_session_setting("prefixes_mode", False) else ""
        with transaction.atomic():
            try:
                log.info(f"{caller}: {line}")
                parse.interpret(ctx, line)
            except exceptions.UserError as e:
                log.error(f"{caller}: {e}")
                exit_status = 1
                output.append(f"[bold red]{prefix}{e}[/bold red]")
            except PermissionError as e:
                log.error(f"{caller}: PermissionError: {e}")
                exit_status = 1
                output.append(f"[bold red]{prefix}PermissionError: {e}[/bold red]")
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.exception(f"Error executing command for {caller}: {e}")
                exit_status = 1
                output.append(f"[bold red]{prefix}An error occurred while executing the command.[/bold red]")
                if caller.is_wizard():
                    import traceback

                    output.append(f"[bold red]{prefix}{traceback.format_exc()}[/bold red]")
        events = code.ContextManager.get("published_events") or []
    if task_id:
        cache.set(f"moo:task_events:{task_id}", list(events), timeout=60)
    return output, exit_status


@shared_task(bind=True)
def parse_code(self, caller_id: int, source: str, runtype: str = "exec") -> tuple[list[Any], Any]:
    """
    Execute code in a task.

    :param caller_id: the PK of the caller of this command
    :param source: the Python code to execute
    :return: a list of output lines and the result value, if any
    """
    output: list[Any] = []
    task_id = self.request.id
    caller = Object.objects.get(pk=caller_id)
    with code.ContextManager(caller, output.append, task_id=task_id):
        with transaction.atomic():
            result = code.interpret(source, "__main__", runtype=runtype)
    return output, result


@shared_task(bind=True)
def invoke_verb(
    self,
    *args,
    caller_id: Optional[int] = None,
    player_id: Optional[int] = None,
    this_id: Optional[int] = None,
    verb_name: Optional[int] = None,
    callback_this_id: Optional[int] = None,
    callback_verb_name: Optional[int] = None,
    **kwargs,
) -> None:
    """
    Asynchronously execute a Verb, optionally returning the result to another Verb.
    The `print()` method routes output to the triggering player's message queue when
    `player_id` is provided, otherwise falls back to the background log.

    :param caller_id: the PK of the context caller (for permission checks)
    :param player_id: the PK of the triggering player; print() output routes to this player
    :param verb_id: the PK of the Verb to execute
    :param callback_verb_id: the PK of the verb to send the result to
    """
    from moo.core import context, _publish_to_player

    task_id = self.request.id
    with transaction.atomic():
        caller = Object.objects.get(pk=caller_id)
        player = Object.objects.get(pk=player_id) if player_id else None
        this = Object.objects.get(pk=this_id)
        verb_obj = this.get_verb(verb_name)
        if player:

            def _player_writer(msg):
                try:
                    _publish_to_player(player, msg)
                except Exception:  # pylint: disable=broad-exception-caught
                    background_log.info(msg)

            writer = _player_writer
        else:
            writer = background_log.info
        from moo.sdk import get_session_setting

        with code.ContextManager(caller, writer, task_id=task_id, player=player):
            prefix = "[ERROR] " if get_session_setting("prefixes_mode", False) else ""
            try:
                result = verb_obj(*args, _bypass_execute_check=True, **kwargs)
            except exceptions.UserError as e:
                log.error(f"{caller}: {e}")
                writer(f"[bold red]{prefix}{e}[/bold red]")
                return
            except PermissionError as e:
                log.error(f"{caller}: PermissionError: {e}")
                writer(f"[bold red]{prefix}PermissionError: {e}[/bold red]")
                return
            except Exception as e:  # pylint: disable=broad-exception-caught
                log.exception(f"Error executing verb {verb_name} for {caller}: {e}")
                writer(f"[bold red]{prefix}An error occurred while executing the verb.[/bold red]")
                if caller.is_wizard():
                    import traceback  # pylint: disable=import-outside-toplevel

                    writer(f"[bold red]{prefix}{traceback.format_exc()}[/bold red]")
                return
            if callback_verb_name and callback_this_id:
                invoke_verb.delay(result, caller_id=caller_id, this_id=callback_this_id, verb_name=callback_verb_name)
