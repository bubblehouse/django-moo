from asgiref.sync import sync_to_async
import builtins
import logging
from typing import Callable

from prompt_toolkit.utils import DummyContext
from prompt_toolkit.formatted_text import AnyFormattedText
from ptpython.repl import PythonRepl
from ptpython.prompt_style import PromptStyle

from ..core import code, models

log = logging.getLogger(__name__)

def embed(
    user: models.User,
    globals=None,
    locals=None,
    configure: Callable[[PythonRepl], None] | None = None,
    vi_mode: bool = False
) -> None:
    """
    Call this to embed  Python shell at the current point in your program.
    It's similar to `IPython.embed` and `bpython.embed`. ::

        from prompt_toolkit.contrib.repl import embed
        embed(globals(), locals())

    :param vi_mode: Boolean. Use Vi instead of Emacs key bindings.
    :param configure: Callable that will be called with the `PythonRepl` as a first
                      argument, to trigger configuration.
    :param patch_stdout:  When true, patch `sys.stdout` so that background
        threads that are printing will print nicely above the prompt.
    """
    # Default globals/locals
    if globals is None:
        globals = {
            "__name__": "__main__",
            "__package__": None,
            "__doc__": None,
            "__builtins__": builtins,
        }

    locals = {}

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
    )

    if configure:
        configure(repl)

    # Start repl.
    async def coroutine() -> None:
        with DummyContext():
            await repl.run_async()

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

    @sync_to_async
    def eval_async(self, line: str) -> object:
        """
        Evaluate the line and print the result.
        """
        if self.prompt_style == "mud":
            return self.prompt_mud(line)
        else:
            return self.prompt_eval(line)

    def prompt_mud(self, line: str) -> object:
        self.app.output.write("Parser not implemented, switch to another mode.\n")

    def prompt_eval(self, line: str) -> object:
        # does this need to be called from outside the synchronous function?
        # Try eval first
        caller = self.user.player.avatar
        log.error(f"{caller}: {line}")
        try:
            with code.context(caller, self.app.output.write) as ctx:
                result = code.do_eval(ctx.caller, line, self.get_locals())
                self._store_eval_result(result)
            return result
        except SyntaxError:
            pass
        # If not a valid `eval` expression, compile as `exec` expression
        # but still run with eval to get an awaitable in case of a
        # awaitable expression.
        with code.context(caller, self.app.output.write) as ctx:
            result = code.do_eval(ctx.caller, line, self.get_locals(), compileas='exec')
        return result
