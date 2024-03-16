import logging
from asgiref.sync import sync_to_async

from prompt_toolkit.utils import DummyContext
from prompt_toolkit.formatted_text import AnyFormattedText
from ptpython.repl import PythonRepl
from ptpython.prompt_style import PromptStyle

from ..core import code, models, parse

log = logging.getLogger(__name__)

def embed(
    user: models.User,
    locals=None,
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
    globals = code.get_default_globals()

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

    globals.update(code.get_restricted_environment(repl.writer))

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

    def writer(self, s, is_error=False):
        if(s.strip()):
            self.app.output.write(f"{s}\n")

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
        """
        Parse the command and execute it.
        """
        caller = self.user.player.avatar
        log.error(f"{caller}: {line}")
        with code.context(caller, self.writer):
            lex = parse.Lexer(line)
            parser = parse.Parser(lex, caller)
            verb = parser.get_verb()
            globals = code.get_restricted_environment(code.context.get('writer'))
            env = {}
            code.r_exec(verb.code, env, globals, filename=repr(self))

    def prompt_eval(self, line: str) -> object:
        # Try eval first
        caller = self.user.player.avatar
        log.error(f"{caller}: {line}")
        try:
            with code.context(caller, self.writer) as ctx:
                result = code.do_eval(line, self.get_locals(), self.get_globals())
                self._store_eval_result(result)
            return result
        except SyntaxError:
            pass
        # If not a valid `eval` expression, compile as `exec` expression
        # but still run with eval to get an awaitable in case of a
        # awaitable expression.
        with code.context(caller, self.writer) as ctx:
            result = code.do_eval(line, self.get_locals(), self.get_globals(), compileas='exec')
        return result
