import asyncio
import logging
import pickle
from asgiref.sync import sync_to_async

from prompt_toolkit import ANSI
from prompt_toolkit.utils import DummyContext
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.shortcuts import print_formatted_text
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.application import run_in_terminal
from ptpython.repl import PythonRepl
from ptpython.prompt_style import PromptStyle
from rich.console import Console
from kombu import simple, Exchange, Queue

from ..core import code, models, tasks
from ..celery import app

log = logging.getLogger(__name__)

def embed(
    user: models.User,
    locals=None,  # pylint: disable=redefined-builtin
    vi_mode: bool = False
) -> None:
    """
    Call this to embed  Python shell at the current point.
    :param vi_mode: Boolean. Use Vi instead of Emacs key bindings.
    :param configure: Callable that will be called with the `PythonRepl` as a first
                      argument, to trigger configuration.
    """
    # Default locals
    locals = {}
    globals = code.get_default_globals()  # pylint: disable=redefined-builtin

    def get_globals():
        return globals
    def get_locals():
        return locals

    # Create REPL.
    repl = CustomRepl(
        user=user,
        get_globals=get_globals,
        get_locals=get_locals,
        vi_mode=vi_mode,
        color_depth=ColorDepth.DEPTH_24_BIT
    )

    globals.update(code.get_restricted_environment(repl.writer))

    # Start repl.
    async def coroutine() -> None:
        await asyncio.wait([asyncio.ensure_future(f()) for f in (
            repl.run_async,
            repl.process_messages
        )])

    return coroutine()  # type: ignore

class MudPrompt(PromptStyle):
    def in_prompt(self) -> AnyFormattedText:
        return [("class:prompt", "==> ")]

    def in2_prompt(self, width: int) -> AnyFormattedText:
        return [("class:prompt.dots", "--> ")]

    def out_prompt(self) -> AnyFormattedText:
        return []

class CustomRepl(PythonRepl):
    def __init__(self, user, *a, **kw):
        self.user = user
        super().__init__(*a, **kw)
        self.all_prompt_styles["mud"] = MudPrompt()
        self.prompt_style = "mud"
        self.enable_syntax_highlighting = False
        self.enable_input_validation = False
        self.complete_while_typing = False
        self.repl_exit = False

    async def run_async(self):
        await super().run_async()
        self.repl_exit = True

    def writer(self, s, is_error=False):
        console = Console(color_system="truecolor")
        with console.capture() as capture:
            console.print(s)
        content = capture.get()
        print_formatted_text(ANSI(content))

    async def process_messages(self) -> None:
        await asyncio.sleep(1)
        try:
            log.debug(f"Scanning for messages for {self.user}")
            with app.default_connection() as conn:
                channel = conn.channel()
                queue = Queue('messages', Exchange('moo', type='direct', channel=channel), f'user-{self.user.pk}', channel=channel)
                while(True):
                    if self.repl_exit:
                        log.debug("REPL is exiting, stopping messages thread...")
                        break
                    sb = simple.SimpleBuffer(channel, queue, no_ack=True)
                    try:
                        msg = sb.get_nowait()
                    except sb.Empty:
                        await asyncio.sleep(1)
                        continue
                    if msg:
                        content = pickle.loads(msg.body)
                        await run_in_terminal(lambda: self.writer(content['message']))
                    sb.close()
        finally:
            pass # cleanup

    @sync_to_async
    def eval_async(self, line: str) -> object:  # pylint: disable=invalid-overridden-method
        """
        Evaluate the line and print the result.
        """
        if self.prompt_style == "mud":
            self.enable_syntax_highlighting = False
            self.enable_input_validation = False
            self.complete_while_typing = False
            return self.prompt_mud(line)
        else:
            self.enable_syntax_highlighting = True
            self.enable_input_validation = True
            self.complete_while_typing = True
            return self.prompt_eval(line)

    def prompt_mud(self, line: str) -> object:
        """
        Parse the command and execute it.
        """
        caller = self.user.player.avatar
        log.info(f"{caller}: {line}")
        ct = tasks.parse_command.delay(caller.pk, line)
        output = ct.get()
        for item in output:
            self.writer(item)

    def prompt_eval(self, line: str) -> object:
        # Try eval first
        caller = self.user.player.avatar
        log.info(f"{caller}: {line}")
        try:
            ct = tasks.parse_code.delay(caller.pk, line)
            output, result = ct.get()
            for item in output:
                self.writer(item)
            self._store_eval_result(result)
            return result
        except SyntaxError:
            pass
        ct = tasks.parse_code.delay(caller.pk, line, runtype="exec")
        output, result = ct.get()
        for item in output:
            self.writer(item)
        return result
