from asgiref.sync import sync_to_async
import builtins
import logging
from typing import Callable

from prompt_toolkit.utils import DummyContext
from ptpython.repl import PythonRepl

from ..core import code

log = logging.getLogger(__name__)

def embed(
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

    locals = locals or globals

    def get_globals():
        return globals

    def get_locals():
        return locals

    # Create REPL.
    repl = CustomRepl(
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

class CustomRepl(PythonRepl):
    @sync_to_async
    def eval_async(self, line: str) -> object:
        """
        Evaluate the line and print the result.
        """
        caller = code.get_caller()
        # Try eval first
        log.error(f"{caller}: {line}")
        try:
            result = code.r_eval(caller, line, self.get_locals())
            self._store_eval_result(result)
            return result
        except SyntaxError:
            pass
        # If not a valid `eval` expression, compile as `exec` expression
        # but still run with eval to get an awaitable in case of a
        # awaitable expression.
        result = code.r_exec(caller, line, self.get_locals())
        return result
