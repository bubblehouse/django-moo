import asyncio
import builtins
from typing import Callable

from prompt_toolkit.utils import DummyContext
from ptpython.repl import PythonRepl

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
    repl = PythonRepl(
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
    def __init__(self, *a, **kw) -> None:
        super().__init__(*a, **kw)
        self._load_start_paths()

    def eval(self, line: str) -> object:
        """
        Evaluate the line and print the result.
        """
        # Try eval first
        try:
            code = self._compile_with_flags(line, "eval")
        except SyntaxError:
            pass
        else:
            # No syntax errors for eval. Do eval.
            result = eval(code, self.get_globals(), self.get_locals())

            result = asyncio.get_event_loop().run_until_complete(result)

            self._store_eval_result(result)
            return result

        # If not a valid `eval` expression, run using `exec` instead.
        # Note that we shouldn't run this in the `except SyntaxError` block
        # above, then `sys.exc_info()` would not report the right error.
        # See issue: https://github.com/prompt-toolkit/ptpython/issues/435
        code = self._compile_with_flags(line, "exec")
        result = eval(code, self.get_globals(), self.get_locals())

        result = asyncio.get_event_loop().run_until_complete(result)

        return None
