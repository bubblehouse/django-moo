"""ZIL routine AST → DjangoMOO Python verb body.

See :doc:`/reference/zil-importer` for the public API and translation
idioms; :doc:`/explanation/zil-importer` for the why."""

from __future__ import annotations

import re
import textwrap
from typing import Any

from .ir import FLAG_PROPERTIES, ZIL_VERBS, ZilRoutine
from .parser import Str


_PY_KEYWORDS = frozenset(
    {
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    }
)

# Python builtins / common names whose collision with a ZIL atom would shadow
# something semantically important. We rename the local rather than the
# builtin so generated code can still call ``set()`` and friends.
_PY_BUILTIN_SHADOWS = frozenset(
    {
        "set",
        "list",
        "dict",
        "tuple",
        "str",
        "int",
        "float",
        "bool",
        "type",
        "id",
        "len",
        "min",
        "max",
        "sum",
        "all",
        "any",
        "map",
        "filter",
        "print",
        "open",
        "input",
        "object",
        "next",
        "iter",
        "range",
    }
)


def _sanitize_ident(name: str) -> str:
    """Convert a ZIL atom into a valid Python identifier.

    See :doc:`Identifier sanitization </reference/zil-importer>`
    for the full rule set. The implementation lower-cases, replaces ``-``
    with ``_``, ``?`` with ``_p``, strips leading ``.``, prefixes leading
    digits with ``v_``, and suffixes Python keywords / shadowed builtins
    with ``_v``."""
    raw = name.lstrip(".")
    out = raw.lower().replace("-", "_").replace("?", "_p")
    out = re.sub(r"[^a-z0-9_]", "_", out)
    if out and out[0].isdigit():
        out = "v_" + out
    if not out:
        return "_unknown"
    if out in _PY_KEYWORDS or out in _PY_BUILTIN_SHADOWS:
        out = out + "_v"
    return out


def _as_object(expr: str) -> str:
    """Wrap a quoted-atom expression in ``lookup()`` for attribute access.

    Bare ``'TROLL'`` is a str literal; ``str.location`` does not exist.
    See :doc:`/explanation/zil-importer` for the rationale."""
    stripped = expr.strip()
    if (
        len(stripped) >= 2
        and stripped[0] in ("'", '"')
        and stripped[-1] == stripped[0]
        and stripped.count(stripped[0]) == 2
    ):
        atom = stripped[1:-1]
        return f'lookup("{atom.lower().replace("-", " ")}")'
    return stripped


# ---------------------------------------------------------------------------
# ZIL property atom → DjangoMOO property name
# ---------------------------------------------------------------------------

_PROP_MAP: dict[str, str] = {
    "P?LDESC": "description",
    "P?FDESC": "first_description",
    "P?DESC": "description",
    "P?ACTION": "action",
    "P?CAPACITY": "capacity",
    "P?SIZE": "size",
    "P?VALUE": "value",
    "P?TVALUE": "tvalue",
    "P?TEXT": "text",
    "P?SYNONYM": "synonyms",
    "P?ADJECTIVE": "adjectives",
    "P?FLAGS": "flags",
    "P?GLOBAL": "global_scenery",
    "P?IN": "location",
    "P?LOC": "location",
    "P?DEST": "dest",
    "P?EXIT": "exit_routine",
    "P?NOGO": "nogo_msg",
    "P?DIR": "direction",
    "P?COND": "condition_flag",
    "P?SCORE": "value",
    "P?STRENGTH": "strength",
    "P?WEAPON": "weapon",
    "P?FIGHTS": "fights",
    "P?MELEE": "melee",
    "P?VILLAINS": "villains",
}

# ---------------------------------------------------------------------------
# ZIL global atom → Python expression
# ---------------------------------------------------------------------------

# Parser / context globals
_GLOBAL_MAP: dict[str, str] = {
    "WINNER": "context.player",
    "HERE": "context.player.location",
    "PRSO": "context.parser.get_dobj()",
    "PRSI": "context.parser.get_iobj()",
    "PRSA": "verb_name",
    "SCORE": "_.zil_sdk.zstate_get('SCORE')",
    "MOVES": "_.zil_sdk.zstate_get('MOVES')",
    "DEATHS": "_.zil_sdk.zstate_get('DEATHS')",
    "VERBOSE-MODE": "_.zil_sdk.zstate_get('VERBOSE-MODE')",
    "SUPERBRIEF": "_.zil_sdk.zstate_get('SUPERBRIEF')",
    "ROOMS": "_.zil_sdk.zstate_get('ROOMS')",
    "P-CONT": "context.player",
    "PLAYER": "context.player",
    "THIEF": 'lookup("thief")',
    "ROBBER": 'lookup("thief")',
    "CYCLOPS": 'lookup("cyclops")',
    "TROLL": 'lookup("troll")',
    "DEMON": 'lookup("demon")',
    "VAMPIRE": 'lookup("vampire bat")',
    "LIT-ROOM": "_.zil_sdk.zstate_get('LIT-ROOM')",
    "ENDGAME": "_.zil_sdk.zstate_get('ENDGAME')",
    "DEAD": "_.zil_sdk.zstate_get('DEAD')",
    "LUCKY": "_.zil_sdk.zstate_get('LUCKY')",
    "LAST-SCORE": "_.zil_sdk.zstate_get('LAST-SCORE')",
}

# ---------------------------------------------------------------------------
# ZIL action M-* constants
# ---------------------------------------------------------------------------

M_CLAUSES = {"M-LOOK", "M-BEG", "M-END", "M-ENTER", "M-LEAVE", "M-FLASH", "M-OBJDESC"}

# ZIL form heads recognised as built-in primitives or SDK calls. Any other
# head is a user routine call worth annotating with its ZIL origin.
_SDK_HEADS: set[str] = {
    # control flow / output
    "RTRUE",
    "RFALSE",
    "RETURN",
    "TELL",
    "CRLF",
    "PRINT",
    "PRINT-CR",
    "PRINTR",
    "PRINTN",
    "PRINTB",
    "PRINTC",
    "COND",
    "AND",
    "OR",
    "NOT",
    "REPEAT",
    "PROG",
    "MAP-CONTENTS",
    "SET",
    # movement / state
    "MOVE",
    "REMOVE",
    "REMOVE-CAREFULLY",
    "GOTO",
    "DO-WALK",
    "FSET",
    "FCLEAR",
    "FSET?",
    "PUTP",
    "GETP",
    "SETG",
    "GVAL",
    "IN?",
    "LOC",
    "FIRST?",
    "FIRST",
    "NEXT?",
    "NEXT",
    "GLOBAL-IN?",
    # arithmetic / comparison
    "+",
    "ADD",
    "-",
    "SUB",
    "*",
    "MUL",
    "/",
    "DIV",
    "MOD",
    "ABS",
    "MIN",
    "MAX",
    "==",
    "==?",
    "EQUAL?",
    "=?",
    "N==?",
    "N=?",
    "G?",
    "GRTR?",
    "L?",
    "LESS?",
    "G=?",
    "L=?",
    "0?",
    "ZERO?",
    "1?",
    # game systems
    "SCORE",
    "JIGS-UP",
    "ENABLE",
    "DISABLE",
    "PERFORM",
    "PICK-ONE",
    "VERB?",
    "RANDOM",
    "PROB",
    "OBJECT-PNAME",
}

_M_TO_VERB: dict[str, str] = {
    "M-LOOK": "look",
    "M-BEG": "confunc",
    "M-END": "turnfunc",
    "M-ENTER": "enterfunc",
    "M-LEAVE": "exitfunc",
}


# ---------------------------------------------------------------------------
# ZilTranslator
# ---------------------------------------------------------------------------


class ZilTranslator:
    """Translate a single ZilRoutine body into Python verb source."""

    def __init__(
        self,
        routine: ZilRoutine,
        object_atoms: set[str] | None = None,
        routine_atoms: set[str] | None = None,
        action_owner: tuple[str, bool] | None = None,
    ) -> None:
        self.routine = routine
        # Atoms that name a Room/Object — used to wrap atom refs as
        # ``lookup("name")`` for attribute access. When unset, falls back to
        # the conservative legacy behaviour (string literal).
        self.object_atoms = {a.upper() for a in (object_atoms or set())}
        # Atoms that name another ZIL routine — used to emit zero-arg
        # routine calls when the atom appears bare in expression position.
        self.routine_atoms = {a.upper() for a in (routine_atoms or set())}
        # ``(atom, is_room)`` of the room/object whose ACTION property points
        # at this routine, or ``None`` for global helpers.  Used by
        # ``_shebang()`` to attach the routine's verb to the specific object
        # so player commands like ``move rug`` find it via dobj search.
        self.action_owner = action_owner
        self._indent = 0
        self._lines: list[str] = []
        self._imports: set[str] = set()
        # Player verb names this routine dispatches on (collected from each
        # ``<VERB? FOO BAR>`` form during ``_translate_body``).  Used by
        # ``_shebang()``.
        self._verbs_handled: set[str] = set()
        # ``<REPEAT … <RETURN>>`` exits the loop, not the function.  Track
        # how many REPEAT bodies we're nested inside so the RETURN handler
        # can emit ``break`` instead of ``return None`` when appropriate.
        self._repeat_depth = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self) -> str:
        """Return the full verb file body as a string."""
        body_lines = self._translate_body(self.routine.body)
        # Make ZIL's implicit-return-of-last-expression explicit.
        body_lines = self._wrap_trailing_return_recursive(body_lines, 0)
        # Per-object ACTION routines that fall off the end need to delegate
        # to the standard V-<verb> routine so default behavior runs (e.g.
        # rope_function's TAKE branch only blocks the dome-tied case; for
        # everything else the standard "Taken." should fire).  Skip global
        # helpers (no action_owner) and skip routines whose body never
        # examines verb_name.
        if self.action_owner and self._verbs_handled:
            body_lines.append("# Auto-generated fallthrough to standard V-<player_verb>")
            body_lines.append("_.zil_sdk.run_v_routine(player_verb)")
        self._auto_import(body_lines)
        imports = self._build_imports()
        header = self._shebang()
        parts = [
            header,
            "# Generated by extras/zil_import — do not edit by hand",
            "# pylint: disable=return-outside-function,undefined-variable,pointless-statement,unnecessary-negation,disallowed-name,using-constant-test,redefined-outer-name,no-else-return,unused-variable,redefined-builtin,singleton-comparison",
        ]
        if imports:
            parts.append(imports)
        parts.append(f"# ZIL routine: {self.routine.name}")
        if self.routine.params:
            parts.append(f"# params: {', '.join(self.routine.params)}")
        if self.routine.aux_vars:
            parts.append(f"# aux: {', '.join(self.routine.aux_vars)}")
        parts.append("")
        # Unpack ZIL params from args so the body can reference them by
        # name. Optional params with declared defaults fall back to that
        # default when ``args`` doesn't supply a value; otherwise to None.
        for i, param in enumerate(self.routine.params):
            default = self.routine.initial_values.get(param)
            default_expr = self._translate_expr(default) if default is not None else "None"
            parts.append(f"{_sanitize_ident(param)} = args[{i}] if len(args) > {i} else {default_expr}")
        # Pre-declare aux vars so branches that bind them satisfy pylint's
        # used-before-assignment check. Aux vars with declared initial
        # values get those; the rest default to None.
        for aux in self.routine.aux_vars:
            default = self.routine.initial_values.get(aux)
            default_expr = self._translate_expr(default) if default is not None else "None"
            parts.append(f"{_sanitize_ident(aux)} = {default_expr}")
        if self.routine.params or self.routine.aux_vars:
            parts.append("")
        parts.extend(body_lines)
        return "\n".join(parts) + "\n"

    def translate_m_clause(self, m_constant: str) -> str:
        """Translate one M-* branch from an ACTION routine, returning the
        clause body as a complete verb file."""
        clause_body = self._extract_m_clause(self.routine.body, m_constant)
        if clause_body is None:
            return f"# No {m_constant} clause found in {self.routine.name}\npass\n"
        body_lines = self._translate_body(clause_body)
        self._auto_import(body_lines)
        imports = self._build_imports()
        header = self._shebang_m(m_constant)
        parts = [
            header,
            "# Generated by extras/zil_import — do not edit by hand",
            "# pylint: disable=return-outside-function,undefined-variable,pointless-statement,unnecessary-negation,disallowed-name,using-constant-test,redefined-outer-name,no-else-return,unused-variable,redefined-builtin,singleton-comparison",
        ]
        if imports:
            parts.append(imports)
        parts.append(f"# ZIL: {self.routine.name} / {m_constant}")
        parts.append("")
        parts.extend(body_lines)
        return "\n".join(parts) + "\n"

    def has_m_dispatch(self) -> bool:
        """Return True if this routine dispatches on M-* constants via COND/RARG."""
        return self._find_m_dispatch(self.routine.body) is not None

    def m_constants_found(self) -> list[str]:
        """Return the list of M-* constants handled by this routine."""
        dispatch = self._find_m_dispatch(self.routine.body)
        if dispatch is None:
            return []
        constants = []
        for clause in dispatch[1:]:
            if not isinstance(clause, (list, tuple)) or not clause:
                continue
            cond = clause[0] if isinstance(clause, (list, tuple)) else None
            if isinstance(cond, (list, tuple)) and len(cond) >= 2:
                # (EQUAL? ,RARG ,M-LOOK) or (==? ,RARG ,M-LOOK)
                for item in cond:
                    if isinstance(item, str) and item in M_CLAUSES:
                        constants.append(item)
            elif isinstance(cond, str) and cond in M_CLAUSES:
                constants.append(cond)
        return constants

    # ------------------------------------------------------------------
    # Shebang generation
    # ------------------------------------------------------------------

    def _shebang(self) -> str:
        name = self.routine.name.lower().replace("_", "-")
        if self.action_owner and self._verbs_handled:
            atom, _is_room = self.action_owner
            verbs = " ".join(sorted(self._verbs_handled))
            owner_prop = atom.lower().replace("-", "_")
            return f"#!moo verb {verbs} --on ${owner_prop} --dspec either"
        return f"#!moo verb {name} --on $zork_thing"

    def _shebang_m(self, m_constant: str) -> str:
        """M-clause splits attach to the routine's action_owner room.

        The previous fallback used ``${routine_name}`` (e.g.
        ``$living_room_fcn``) — an object that doesn't exist, so the verb
        never reached its target room.  When ``action_owner`` is present
        we resolve to the actual room property (``$living_room``); for
        orphan routines (no action_owner) we keep the legacy fallback so
        callers don't crash, even though that path can't dispatch.
        """
        verb = _M_TO_VERB.get(m_constant, m_constant.lower().replace("m-", ""))
        if self.action_owner:
            atom, _is_room = self.action_owner
            owner_prop = atom.lower().replace("-", "_")
            return f"#!moo verb {verb} --on ${owner_prop}"
        name = self.routine.name.lower().replace("_", "-")
        return f"#!moo verb {verb} --on ${name.replace('-', '_')}"

    # ------------------------------------------------------------------
    # Import bookkeeping
    # ------------------------------------------------------------------

    def _need_import(self, name: str) -> None:
        self._imports.add(name)

    # Token-level patterns the auto-importer looks for after body
    # translation so callers don't have to thread import bookkeeping
    # through every emission site.
    _AUTO_IMPORT_PATTERNS = (
        ("lookup", re.compile(r"\blookup\(")),
        ("context", re.compile(r"\bcontext\.")),
        ("random", re.compile(r"\brandom\.")),
        ("re", re.compile(r"\bre\.")),
    )

    def _auto_import(self, lines: list[str]) -> None:
        """Scan generated body lines and register any required imports."""
        body = "\n".join(lines)
        for name, pattern in self._AUTO_IMPORT_PATTERNS:
            if pattern.search(body):
                self._need_import(name)

    # Names emitted as plain ``import X`` rather than ``from moo.sdk import X``.
    # ``random`` is a stdlib module that the verb sandbox allows — it does not
    # live under ``moo.sdk``.
    _STDLIB_IMPORTS = frozenset({"random", "re", "hashlib", "datetime", "time"})

    def _build_imports(self) -> str:
        if not self._imports:
            return ""
        stdlib = sorted(n for n in self._imports if n in self._STDLIB_IMPORTS)
        sdk = sorted(n for n in self._imports if n not in self._STDLIB_IMPORTS)
        lines = [f"import {n}" for n in stdlib]
        if sdk:
            lines.append(f"from moo.sdk import {', '.join(sdk)}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Body translation
    # ------------------------------------------------------------------

    def _translate_body(self, forms: list, indent: int = 0) -> list[str]:
        """Translate a sequence of forms as statement lines."""
        lines = []
        for form in forms:
            result = self._translate_stmt(form, indent)
            lines.extend(result)
        if not lines:
            lines.append(self._indent_str(indent) + "pass")
            return lines
        # Python requires a real statement in every block. If every line is
        # a comment, append a ``pass`` so the block parses.
        if all(not line.strip() or line.lstrip().startswith("#") for line in lines):
            lines.append(self._indent_str(indent) + "pass")
        return lines

    def _indent_str(self, indent: int) -> str:
        return "    " * indent

    def _translate_stmt(self, form: Any, indent: int = 0) -> list[str]:
        """Translate one form as a statement, returning lines."""
        ind = self._indent_str(indent)

        if form is None or (isinstance(form, list) and not form):
            return []

        # Skip ZIL declaration forms (<#DECL ...>) — they are type hints for
        # the original compiler, not runtime behaviour.
        if isinstance(form, list) and form and isinstance(form[0], str) and form[0].upper() in ("#DECL", "DECL"):
            return []

        if isinstance(form, (int, str)) and not isinstance(form, list):
            # Bare atom or number at statement position — usually ZIL's
            # implicit-return-of-last-expression idiom (e.g. CCOUNT ends
            # with bare ``.CNT``).  Emit it as an expression line so the
            # trailing-return wrapper can pick it up; mid-body bare atoms
            # are a no-op in Python which matches their ZIL semantics.
            expr = self._translate_expr(form)
            return [f"{ind}{expr}"]

        # Parenthesised groups are ZIL declaration / property syntax (e.g.
        # the body of ``#DECL ((VAR ...) TYPE)``). They never produce
        # runtime behaviour at the statement level.
        if isinstance(form, tuple):
            return []

        if not isinstance(form, list):
            return [f"{ind}# ZIL: {form!r}", f"{ind}pass"]

        head = form[0] if form else None
        if not isinstance(head, str):
            expr = self._translate_expr(form)
            return [f"{ind}{expr}"]

        head = head.upper()

        # --- return/control ---
        if head == "RTRUE":
            return [f"{ind}return True"]
        if head == "RFALSE":
            return [f"{ind}return False"]
        if head == "RETURN":
            # Bare ``<RETURN>`` inside a ``<REPEAT …>`` exits the loop,
            # not the routine.  ``<RETURN value>`` always returns from the
            # routine even inside REPEAT (ZIL semantics — the value form
            # signals an explicit routine return).
            if len(form) <= 1 and self._repeat_depth > 0:
                return [f"{ind}break"]
            val = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}return {val}"]

        # --- output ---
        if head == "TELL":
            return [f"{ind}{self._translate_tell(form)}"]
        if head == "CRLF":
            return [f"{ind}print()"]
        if head == "PRINT":
            val = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}print({val}, end='')"]
        if head in ("PRINT-CR", "PRINTR"):
            val = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}print({val})"]
        if head == "PRINTN":
            val = self._translate_expr(form[1]) if len(form) > 1 else "0"
            return [f"{ind}print(str({val}), end='')"]
        if head == "PRINTB":
            val = self._translate_expr(form[1]) if len(form) > 1 else "0"
            return [f"{ind}print(str({val}), end='')"]
        if head == "PRINTC":
            val = self._translate_expr(form[1]) if len(form) > 1 else "0"
            return [f"{ind}print(chr({val}), end='')"]

        # --- conditionals ---
        if head == "COND":
            return self._translate_cond(form, indent)
        if head == "AND":
            # AND-as-statement → nested if-chain; see _translate_short_circuit.
            return self._translate_short_circuit(form[1:], indent, negate=False)
        if head == "OR":
            return self._translate_short_circuit(form[1:], indent, negate=True)
        if head == "NOT":
            val = self._translate_expr(form[1]) if len(form) > 1 else "True"
            return [f"{ind}not {val}"]

        # --- loops ---
        if head == "REPEAT":
            body = list(form[2:]) if len(form) > 2 else list(form[1:])
            self._repeat_depth += 1
            try:
                inner = self._translate_body(body, indent + 1)
            finally:
                self._repeat_depth -= 1
            return [f"{ind}while True:"] + inner

        if head == "PROG":
            # (PROG () body...) — inline block
            body = list(form[2:]) if len(form) > 2 and isinstance(form[1], (list, tuple)) else list(form[1:])
            return self._translate_body(body, indent)

        if head == "MAP-CONTENTS":
            # (MAP-CONTENTS (var obj) body...)
            if len(form) > 2 and isinstance(form[1], (list, tuple)):
                var_list = form[1]
                var_name = _sanitize_ident(str(var_list[0])) if var_list else "item"
                container = _as_object(self._translate_expr(var_list[1])) if len(var_list) > 1 else "this"
                body = list(form[2:])
                inner = self._translate_body(body, indent + 1)
                return [f"{ind}for {var_name} in {container}.contents.all():"] + inner
            return [f"{ind}# ZIL: {form!r}  (MAP-CONTENTS not translated)"]

        # --- movement ---
        if head == "MOVE":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            dest = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}_.zil_sdk.move({obj}, {dest})"]
        if head in ("REMOVE", "REMOVE-CAREFULLY"):
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}_.zil_sdk.remove({obj})"]
        if head == "GOTO":
            room = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}_.zil_sdk.goto({room})"]
        if head == "DO-WALK":
            direction = self._translate_expr(form[1]) if len(form) > 1 else '"north"'
            return [f"{ind}_.zil_sdk.walk({direction})"]

        # --- flags ---
        if head == "FSET":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            flag = self._translate_flag_name(form[2]) if len(form) > 2 else '"unknown"'
            return [f"{ind}_.zil_sdk.set_flag({obj}, {flag}, True)"]
        if head == "FCLEAR":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            flag = self._translate_flag_name(form[2]) if len(form) > 2 else '"unknown"'
            return [f"{ind}_.zil_sdk.set_flag({obj}, {flag}, False)"]

        # --- properties ---
        if head == "PUTP":
            obj = _as_object(self._translate_expr(form[1])) if len(form) > 1 else "None"
            prop = self._translate_prop_name(form[2]) if len(form) > 2 else '"unknown"'
            val = self._translate_expr(form[3]) if len(form) > 3 else "None"
            return [f"{ind}{obj}.set_property({prop}, {val})"]

        # --- global state ---
        if head == "SETG":
            key = str(form[1]).upper() if len(form) > 1 else "UNKNOWN"
            val = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}_.zil_sdk.zstate_set({repr(key)}, {val})"]

        # --- score ---
        if head == "SCORE":
            delta = self._translate_expr(form[1]) if len(form) > 1 else "0"
            return [f"{ind}_.zil_sdk.score_update({delta})"]

        # --- death ---
        if head == "JIGS-UP":
            msg = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}_.zil_sdk.jigs_up({msg})"]

        # --- queue/interrupts ---
        if head == "ENABLE":
            inner = form[1] if len(form) > 1 else None
            if isinstance(inner, list) and inner:
                inner_head = str(inner[0]).upper()
                if inner_head == "QUEUE":
                    routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                    delay = self._translate_expr(inner[2]) if len(inner) > 2 else "1"
                    return [f"{ind}_.zil_sdk.queue({routine}, {delay})"]
                if inner_head == "INT":
                    routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                    return [f"{ind}_.zil_sdk.queue({routine}, 0)"]
            return [f"{ind}# ZIL: {form!r}  (ENABLE not translated)"]
        if head == "DISABLE":
            inner = form[1] if len(form) > 1 else None
            if isinstance(inner, list):
                routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                return [f"{ind}_.zil_sdk.cancel({routine})"]
            return [f"{ind}# ZIL: {form!r}  (DISABLE not translated)"]

        # --- perform (indirect verb call) ---
        if head == "PERFORM":
            verb_atom = self._translate_expr(form[1]) if len(form) > 1 else '"unknown"'
            prso = self._translate_expr(form[2]) if len(form) > 2 else "None"
            prsi = self._translate_expr(form[3]) if len(form) > 3 else "None"
            return [f"{ind}_.zil_sdk.perform({verb_atom}, {prso}, {prsi})"]

        # --- local set ---
        if head == "SET":
            var = _sanitize_ident(str(form[1])) if len(form) > 1 else "v_unknown"
            val = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}{var} = {val}"]

        # --- everything else: try as expression statement ---
        expr = self._translate_expr(form)
        # Annotate untranslated fallbacks (`None`) so the original ZIL form
        # is recoverable in the generated source for debugging.
        if expr == "None" and isinstance(form, list):
            comment = repr(form)[:120]
            return [f"{ind}# ZIL: {comment}", f"{ind}pass"]
        # Annotate routine calls that we don't recognise as SDK helpers, so
        # the original ZIL head is preserved next to the call site.
        if isinstance(form, list) and form and isinstance(form[0], str):
            head_atom = form[0].upper()
            if head_atom not in _SDK_HEADS and head_atom[0].isalpha() and not head_atom.startswith("V?"):
                return [f"{ind}# ZIL: <{form[0]} ...>", f"{ind}{expr}"]
        return [f"{ind}{expr}"]

    # ------------------------------------------------------------------
    # Expression translation
    # ------------------------------------------------------------------

    def _translate_expr(self, node: Any) -> str:
        """Translate a ZIL node as a Python expression."""
        if node is None:
            return "False"
        if isinstance(node, bool):
            return str(node)
        if isinstance(node, int):
            return str(node)
        # ZIL string literal — emit a Python string with the same content.
        # Must be checked BEFORE ``isinstance(node, str)`` because Str is a
        # subclass of str.
        if isinstance(node, Str):
            return repr(str(node))

        if isinstance(node, str):
            # Bare atom. Strip ZIL ``,X`` / ``.X`` deref prefix before classifying.
            atom = node.lstrip(",.")
            upper = atom.upper()
            if upper == "T":
                return "True"
            if upper == "FALSE" or upper == "<>":
                return "False"
            if upper in (p.upper() for p in self.routine.params + self.routine.aux_vars):
                return _sanitize_ident(upper)
            if upper in _GLOBAL_MAP:
                return _GLOBAL_MAP[upper]
            if upper in M_CLAUSES:
                # M-* event constants used in <EQUAL? .RARG ,M-LOOK>
                return repr(upper)
            if upper in self.object_atoms:
                # Bootstrap stores `_.set_property(atom_lower_underscore,
                # obj)` for every room/object, so reading the atom via
                # `_.<atom>` is reliable regardless of the object's DESC.
                # `lookup()` by name would miss rooms whose DESC differs
                # from the atom (e.g. SOUTH-TEMPLE → "Altar").
                prop = atom.lower().replace("-", "_")
                return f"_.get_property({prop!r})"
            if upper in self.routine_atoms:
                return f"_.zork_thing.invoke_verb({repr(atom.lower())})"
            # Default: global state variable read.
            return f"_.zil_sdk.zstate_get({repr(upper)})"

        if isinstance(node, tuple):
            # Group — usually not an expression in this context
            return repr(list(node))

        if not isinstance(node, list):
            return repr(node)

        if not node:
            return "False"

        head = node[0]
        if not isinstance(head, str):
            return repr(node)
        head_upper = head.upper()

        # --- arithmetic ---
        if head_upper in ("+", "ADD"):
            return " + ".join(self._translate_expr(a) for a in node[1:])
        if head_upper in ("-", "SUB"):
            if len(node) == 2:
                return f"-{self._translate_expr(node[1])}"
            return " - ".join(self._translate_expr(a) for a in node[1:])
        if head_upper in ("*", "MUL"):
            return " * ".join(self._translate_expr(a) for a in node[1:])
        if head_upper in ("/", "DIV"):
            return " // ".join(self._translate_expr(a) for a in node[1:])
        if head_upper == "MOD":
            a, b = node[1], node[2]
            return f"{self._translate_expr(a)} % {self._translate_expr(b)}"
        if head_upper == "ABS":
            return f"abs({self._translate_expr(node[1])})"
        if head_upper == "MIN":
            args = ", ".join(self._translate_expr(a) for a in node[1:])
            return f"min({args})"
        if head_upper == "MAX":
            args = ", ".join(self._translate_expr(a) for a in node[1:])
            return f"max({args})"

        # --- comparison ---
        if head_upper in ("==", "EQUAL?", "=?", "==?"):
            if len(node) == 3:
                return f"{self._translate_expr(node[1])} == {self._translate_expr(node[2])}"
            # Multi-way equality: (EQUAL? a b c) → a in (b, c)
            lhs = self._translate_expr(node[1])
            rhs = ", ".join(self._translate_expr(a) for a in node[2:])
            return f"{lhs} in ({rhs})"
        if head_upper in ("N==?", "N=?"):
            return f"{self._translate_expr(node[1])} != {self._translate_expr(node[2])}"
        if head_upper in ("G?", "GRTR?"):
            return f"{self._translate_expr(node[1])} > {self._translate_expr(node[2])}"
        if head_upper in ("L?", "LESS?"):
            return f"{self._translate_expr(node[1])} < {self._translate_expr(node[2])}"
        if head_upper in ("G=?",):
            return f"{self._translate_expr(node[1])} >= {self._translate_expr(node[2])}"
        if head_upper in ("L=?",):
            return f"{self._translate_expr(node[1])} <= {self._translate_expr(node[2])}"
        if head_upper in ("0?", "ZERO?"):
            return f"{self._translate_expr(node[1])} == 0"
        if head_upper == "1?":
            return f"{self._translate_expr(node[1])} == 1"

        # --- logic ---
        if head_upper == "AND":
            return " and ".join(self._translate_expr(a) for a in node[1:])
        if head_upper == "OR":
            return " or ".join(self._translate_expr(a) for a in node[1:])
        if head_upper == "NOT":
            return f"not {self._translate_expr(node[1])}"

        # --- flags ---
        if head_upper == "FSET?":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            flag = self._translate_flag_name(node[2]) if len(node) > 2 else '"unknown"'
            return f"_.zil_sdk.flag({obj}, {flag})"

        # --- object containment / location ---
        if head_upper == "IN?":
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            container = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"{obj}.location == {container}"
        if head_upper == "LOC":
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            return f"{obj}.location"
        if head_upper in ("FIRST?", "FIRST"):
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            # ``next(iter(...))`` isn't available in the sandbox; ``.first()``
            # is the Django ORM helper that returns the first row or ``None``.
            return f"{obj}.contents.first()"
        if head_upper in ("NEXT?", "NEXT"):
            # ZIL linked-list iteration: ``<NEXT? .CONT>`` returns the next
            # sibling in CONT.LOCATION's contents (or FALSE).  ``next_sibling``
            # in zil_sdk implements this with pk ordering for determinism.
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            return f"_.zil_sdk.next_sibling({obj})"
        if head_upper == "GLOBAL-IN?":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            loc = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"_.zil_sdk.global_in({obj}, {loc})"

        # --- ZIL macros ---
        if head_upper == "RFATAL":
            # ``<RFATAL>`` macro expands to ``<PROG () <PUSH 2> <RSTACK>>`` —
            # it returns the constant 2 from the enclosing routine via the
            # call stack.  We just emit ``return 2`` since callers check
            # the value with ``<EQUAL? ... T>`` (which is False for 2,
            # matching the "fatal" branch).
            return "2"

        # --- table ops (ZIL Z-machine PUT/GET on word tables) ---
        if head_upper == "PUT":
            table = self._translate_expr(node[1]) if len(node) > 1 else "None"
            idx = self._translate_expr(node[2]) if len(node) > 2 else "0"
            val = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"_.zil_sdk.table_put({table}, {idx}, {val})"
        if head_upper in ("GET", "GETB"):
            table = self._translate_expr(node[1]) if len(node) > 1 else "None"
            idx = self._translate_expr(node[2]) if len(node) > 2 else "0"
            return f"_.zil_sdk.table_get({table}, {idx})"

        # --- properties ---
        if head_upper == "GETP":
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            prop = self._translate_prop_name(node[2]) if len(node) > 2 else '"unknown"'
            return f"{obj}.get_property({prop})"
        if head_upper == "PUTP":
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            prop = self._translate_prop_name(node[2]) if len(node) > 2 else '"unknown"'
            val = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"{obj}.set_property({prop}, {val})"

        # --- global state read ---
        if head_upper == "SETG":
            key = str(node[1]).upper() if len(node) > 1 else "UNKNOWN"
            val = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"_.zil_sdk.zstate_set({repr(key)}, {val})"
        if head_upper == "GVAL":
            key = str(node[1]).upper() if len(node) > 1 else "UNKNOWN"
            if key in _GLOBAL_MAP:
                return _GLOBAL_MAP[key]
            return f"_.zil_sdk.zstate_get({repr(key)})"

        # --- output ---
        if head_upper == "TELL":
            return self._translate_tell(node)
        if head_upper == "CRLF":
            return "print()"
        if head_upper in ("PRINT", "PRINTR", "PRINT-CR"):
            val = self._translate_expr(node[1]) if len(node) > 1 else '""'
            return f"print({val})"
        if head_upper == "PRINTN":
            val = self._translate_expr(node[1]) if len(node) > 1 else "0"
            return f"print(str({val}), end='')"
        if head_upper == "PRINTC":
            val = self._translate_expr(node[1]) if len(node) > 1 else "0"
            return f"print(chr({val}), end='')"
        if head_upper == "PICK-ONE":
            table = self._translate_expr(node[1]) if len(node) > 1 else '"unknown"'
            return f"_.zil_sdk.pick({table})"

        # --- verb dispatch ---
        if head_upper == "VERB?":
            verbs = [str(v).upper() for v in node[1:] if isinstance(v, str)]
            aliases: list[str] = []
            for v in verbs:
                aliases.extend(ZIL_VERBS.get(v, [v.lower()]))
            self._verbs_handled.update(aliases)
            # ``player_verb`` is the parser's matched player verb (ZIL PRSA)
            # — preserved across cross-routine ``invoke_verb`` calls.  Each
            # translated routine's invoked ``verb_name`` may differ when
            # called programmatically (e.g. trap_door_fcn → open-close).
            return f"player_verb in {aliases!r}"

        # --- random ---
        if head_upper == "RANDOM":
            n = self._translate_expr(node[1]) if len(node) > 1 else "6"
            return f"random.randint(1, {n})"
        if head_upper == "PROB":
            n = self._translate_expr(node[1]) if len(node) > 1 else "50"
            return f"random.randint(1, 100) <= {n}"

        # --- score ---
        if head_upper == "SCORE":
            delta = self._translate_expr(node[1]) if len(node) > 1 else "0"
            return f"_.zil_sdk.score_update({delta})"

        # --- death ---
        if head_upper == "JIGS-UP":
            msg = self._translate_expr(node[1]) if len(node) > 1 else '""'
            return f"_.zil_sdk.jigs_up({msg})"

        # --- desc ---
        if head_upper in ("OBJECT-PNAME",):
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f"_.zil_sdk.desc({obj})"

        # --- perform ---
        if head_upper == "PERFORM":
            verb_atom = self._translate_expr(node[1]) if len(node) > 1 else '"unknown"'
            prso = self._translate_expr(node[2]) if len(node) > 2 else "None"
            prsi = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"_.zil_sdk.perform({verb_atom}, {prso}, {prsi})"

        # --- SET as expression: walrus binds the local var ---
        if head_upper == "SET":
            var = _sanitize_ident(str(node[1])) if len(node) > 1 else "v_unknown"
            val = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"({var} := {val})"

        # --- variable / global dereference by head alone ---
        # Some constructs like (,LAMP) are parsed as a list with one string element
        if len(node) == 1 and isinstance(node[0], str):
            atom = node[0].upper()
            if atom in _GLOBAL_MAP:
                return _GLOBAL_MAP[atom]
            # Predicate atoms (FOO?) are zero-arg routine calls, not objects.
            if atom.endswith("?"):
                return f"{_sanitize_ident(atom)}()"
            # Known routine call (e.g. ``<ITAKE>`` from ``<EQUAL? <ITAKE> T>``)
            # — must be invoked rather than looked up as an object.
            if atom in self.routine_atoms:
                return f"_.zork_thing.invoke_verb({repr(atom.lower())})"
            # Object reference: look up by name (strip ZIL suffixes)
            obj_name = atom.lower().replace("-", " ")
            return f'lookup("{obj_name}")'

        # Bare atom references that appear as the head with no args
        if head_upper in _GLOBAL_MAP:
            return _GLOBAL_MAP[head_upper]

        # Routine call. Known names dispatch to ``$zork_thing`` verbs;
        # unknown ones become plain calls and surface as NameError at runtime.
        if head_upper[0].isalpha() and not head_upper.startswith("V?"):
            args_expr = ", ".join(self._translate_expr(a) for a in node[1:])
            if head_upper in self.routine_atoms:
                verb_name = head_upper.lower()
                if args_expr:
                    return f"_.zork_thing.invoke_verb({verb_name!r}, {args_expr})"
                return f"_.zork_thing.invoke_verb({verb_name!r})"
            func_name = _sanitize_ident(head_upper)
            return f"{func_name}({args_expr})"

        # Unrecognised — bare ``None``. The statement-level emitter
        # attaches a ``# ZIL: ...`` annotation; doing it here would break
        # parsing when the expression is later nested.
        return "None"

    # ------------------------------------------------------------------
    # TELL translation
    # ------------------------------------------------------------------

    def _translate_tell(self, form: list) -> str:
        """Translate a <TELL ...> form into a print() call."""
        parts = form[1:]
        segments: list[str] = []
        has_cr = False

        i = 0
        while i < len(parts):
            item = parts[i]
            if isinstance(item, str) and item.upper() == "CR":
                has_cr = True
                i += 1
                continue
            if isinstance(item, str) and item.upper() == "D":
                # D ,OBJ — description of next argument
                i += 1
                if i < len(parts):
                    obj = self._translate_expr(parts[i])
                    segments.append(f"_.zil_sdk.desc({obj})")
                i += 1
                continue
            if isinstance(item, str) and item.upper() == "N":
                # N ,EXPR — numeric value of next argument
                i += 1
                if i < len(parts):
                    val = self._translate_expr(parts[i])
                    segments.append(f"str({val})")
                i += 1
                continue
            if isinstance(item, str) and item.upper() == "C":
                # C ,CHAR — character value
                i += 1
                if i < len(parts):
                    val = self._translate_expr(parts[i])
                    segments.append(f"chr({val})")
                i += 1
                continue
            if isinstance(item, str) and item.upper() == "B":
                # B ,val — byte/number
                i += 1
                if i < len(parts):
                    val = self._translate_expr(parts[i])
                    segments.append(f"str({val})")
                i += 1
                continue
            # Plain string or expression
            expr = self._translate_expr(item)
            segments.append(expr)
            i += 1

        if not segments:
            if has_cr:
                return "print()"
            return "print('', end='')"

        joined = " + ".join(segments)
        if has_cr:
            return f"print({joined})"
        return f"print({joined}, end='')"

    # ------------------------------------------------------------------
    # COND translation
    # ------------------------------------------------------------------

    def _translate_short_circuit(self, operands: list, indent: int, negate: bool) -> list[str]:
        """Translate ``<AND ...>`` / ``<OR ...>`` as a statement chain.

        Emits nested ``if`` blocks so the trailing operand runs as a real
        statement. See :doc:`Translation idioms </reference/zil-importer>`."""
        if not operands:
            return []
        if len(operands) == 1:
            return self._translate_stmt(operands[0], indent)
        head_expr = self._translate_expr(operands[0])
        if negate:
            head_expr = f"not {head_expr}"
        ind = self._indent_str(indent)
        inner = self._translate_short_circuit(operands[1:], indent + 1, negate)
        # Python requires a real statement in the inner block. If every
        # generated line is a comment, append ``pass`` so the block parses.
        if inner and all(not l.strip() or l.lstrip().startswith("#") for l in inner):
            inner.append(self._indent_str(indent + 1) + "pass")
        elif not inner:
            inner = [self._indent_str(indent + 1) + "pass"]
        return [f"{ind}if {head_expr}:"] + inner

    def _translate_cond(self, form: list, indent: int) -> list[str]:
        """Translate <COND (cond body...) (cond body...) (T body...)>."""
        ind = self._indent_str(indent)
        lines = []
        clauses = self._splice_zorknumber_macros(form[1:])

        first_emitted = True
        for clause in clauses:
            if not isinstance(clause, (list, tuple)) or not clause:
                continue
            cond = clause[0]
            body = list(clause[1:])

            # T / ELSE clause
            is_else = isinstance(cond, str) and cond.upper() in ("T", "ELSE")

            if is_else:
                # An ``else`` is only legal after an emitted ``if``/``elif``.
                # If the previous clauses all had unrecognised conditions
                # the chain hasn't started — fall back to ``if True``.
                lines.append(f"{ind}else:" if not first_emitted else f"{ind}if True:")
                first_emitted = False
            else:
                cond_expr = self._translate_expr(cond)
                if cond_expr == "None":
                    # Unrecognised condition — emit an always-false placeholder
                    # branch so subsequent ``elif``/``else`` clauses still
                    # have a valid chain to attach to. The pylint disable
                    # silences the constant-test warning since this is a
                    # documented translation gap, not a bug in the output.
                    keyword = "if" if first_emitted else "elif"
                    lines.append(f"{ind}{keyword} False:  # pylint: disable=using-constant-test")
                    lines.append(f"{ind}    # ZIL: unrecognised condition {cond!r}")
                    lines.append(f"{ind}    pass")
                    first_emitted = False
                    continue
                keyword = "if" if first_emitted else "elif"
                lines.append(f"{ind}{keyword} {cond_expr}:")
                first_emitted = False

            if body:
                body_lines = self._translate_body(body, indent + 1)
                lines.extend(body_lines)
            else:
                lines.append(f"{ind}    pass")

        return lines

    def _splice_zorknumber_macros(self, clauses):
        """Resolve substrate ``%<COND ... ZORK-NUMBER ...>`` macros at
        translate time.

        The substrate uses the read-time ``%`` splice operator to pick a
        body based on the compile-time ``ZORK-NUMBER`` constant.  Our
        tokenizer drops ``%`` and ``'``, so the parser sees the inner
        ``<COND>`` as the outer COND's first conditional — yielding nonsense
        like ``if zstate("COND")``.

        For Zork 1 (the only target right now) we treat ``ZORK-NUMBER`` as
        ``1``.  This walks the COND's clauses, and if any clause's
        condition is itself a ``COND`` whose first sub-clause's condition
        is ``<==? ,ZORK-NUMBER N>``, we splice the matching body's clauses
        in place of that outer clause.  Non-matching macros pass through
        unchanged so we don't break unrelated patterns.
        """
        zork_number = 1  # all current targets are Zork 1
        spliced = []
        for clause in clauses:
            if (
                isinstance(clause, list)
                and len(clause) >= 2
                and isinstance(clause[0], str)
                and clause[0].upper() == "COND"
            ):
                # ``[COND, (test, body), (T, body), ...]`` — pick matching body.
                replacement = None
                for sub in clause[1:]:
                    if not isinstance(sub, (list, tuple)) or len(sub) < 2:
                        continue
                    test = sub[0]
                    body = sub[1]
                    is_match = False
                    if isinstance(test, str) and test.upper() in ("T", "ELSE"):
                        is_match = True
                    elif (
                        isinstance(test, list)
                        and len(test) >= 3
                        and isinstance(test[0], str)
                        and test[0].upper() in ("==?", "EQUAL?")
                        and isinstance(test[1], str)
                        and test[1].upper() == "ZORK-NUMBER"
                        and test[2] == zork_number
                    ):
                        is_match = True
                    if is_match:
                        replacement = body
                        break
                if replacement is not None:
                    # ``body`` is typically a quoted-list — a single tuple/list of
                    # forms — but the dropped quote means it appears as a tuple.
                    # Splice each contained form as a separate clause; if it's a
                    # single non-tuple form, treat it as one whole clause.
                    if isinstance(replacement, tuple):
                        # Tuple from `(...)` group — its elements become the
                        # outer COND clauses.  Each element may itself be a
                        # `(test body...)` group.
                        spliced.append(replacement)
                    else:
                        spliced.append(replacement)
                    continue
            spliced.append(clause)
        return spliced

    _CONTROL_PREFIXES = ("if ", "elif ", "else", "while ", "for ", "return", "raise", "pass", "break", "continue", "#")
    # ``var = expr`` (one or more dots allowed for attribute assignments)
    # but NOT ``var == expr`` or ``var != expr``. The negative lookbehind
    # rules out comparison operators and walrus.
    _ASSIGN_RE = re.compile(r"^[A-Za-z_][\w.\[\]]*\s*(?<![=!<>])=(?!=)")

    def _line_indent(self, line: str) -> int:
        """Return the leading-space indent of ``line`` rounded down to 4."""
        n = len(line) - len(line.lstrip(" "))
        return n // 4

    def _wrap_trailing_return_recursive(self, lines: list[str], indent: int) -> list[str]:
        """Recursively wrap the trailing expression of every branch in
        ``return``. Implements ZIL's implicit-return-of-last-expression —
        see :doc:`/explanation/zil-importer`."""
        if not lines:
            return lines
        # Find the last non-blank, non-comment line whose indent matches
        # ``indent``. That is the routine's tail at this scope.
        tail_idx: int | None = None
        for idx in range(len(lines) - 1, -1, -1):
            line = lines[idx]
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if self._line_indent(line) == indent:
                tail_idx = idx
                break
        if tail_idx is None:
            return lines
        tail_line = lines[tail_idx]
        stripped = tail_line.strip()
        if stripped.startswith(self._CONTROL_PREFIXES) and not stripped.startswith(
            ("if ", "elif ", "else", "while ", "for ")
        ):
            return lines
        if stripped.startswith(("if ", "elif ", "else", "while ", "for ")):
            # Walk the chain of openers at this indent and recurse into
            # each block body so every branch's tail gets the wrap.
            for opener_idx in range(tail_idx + 1):
                opener = lines[opener_idx]
                if self._line_indent(opener) != indent:
                    continue
                if not opener.lstrip().startswith(("if ", "elif ", "else", "while ", "for ")):
                    continue
                block_end = opener_idx + 1
                while block_end < len(lines):
                    bl = lines[block_end]
                    if bl.strip() and self._line_indent(bl) <= indent:
                        break
                    block_end += 1
                nested = self._wrap_trailing_return_recursive(lines[opener_idx + 1 : block_end], indent + 1)
                lines[opener_idx + 1 : block_end] = nested
            return lines
        # Bare trailing expression — wrap in ``return``. Skip assignments
        # (``x = y``) because that's a statement, not an expression.
        if self._ASSIGN_RE.match(stripped):
            return lines
        prefix = " " * (indent * 4)
        lines[tail_idx] = f"{prefix}return {stripped}"
        return lines

    # ------------------------------------------------------------------
    # M-* clause extraction
    # ------------------------------------------------------------------

    def _find_m_dispatch(self, forms: list) -> list | None:
        """Find a top-level COND that dispatches on RARG/M-* constants."""
        for form in forms:
            if not isinstance(form, list) or not form:
                continue
            head = str(form[0]).upper()
            if head == "COND":
                for clause in form[1:]:
                    if not isinstance(clause, (list, tuple)) or not clause:
                        continue
                    cond = clause[0]
                    if isinstance(cond, (list, tuple)):
                        for item in cond:
                            if isinstance(item, str) and item in M_CLAUSES:
                                return form
                    elif isinstance(cond, str) and cond in M_CLAUSES:
                        return form
        return None

    def _extract_m_clause(self, forms: list, m_constant: str) -> list | None:
        """Return body forms for the given M-* clause, or None."""
        dispatch = self._find_m_dispatch(forms)
        if dispatch is None:
            return None

        for clause in dispatch[1:]:
            if not isinstance(clause, (list, tuple)) or not clause:
                continue
            cond = clause[0]
            body = list(clause[1:])

            if isinstance(cond, str) and cond.upper() == m_constant:
                return body
            if isinstance(cond, (list, tuple)):
                for item in cond:
                    if isinstance(item, str) and item.upper() == m_constant:
                        return body
            # T/ELSE clause — treat as M-LOOK fallback if no explicit match found
        return None

    # ------------------------------------------------------------------
    # Flag / property name helpers
    # ------------------------------------------------------------------

    def _translate_flag_name(self, node: Any) -> str:
        """Translate a ZIL flag atom to the DjangoMOO property name string."""
        if isinstance(node, list) and node:
            # ,FLAGNAME is parsed as a list [FLAGNAME] in some contexts
            node = node[0] if len(node) == 1 else node
        if isinstance(node, str):
            upper = node.upper()
            if upper in FLAG_PROPERTIES:
                prop, _val = FLAG_PROPERTIES[upper]
                return repr(prop)
            # strip P? prefix
            if upper.startswith("P?"):
                upper = upper[2:]
            return repr(upper.lower().replace("-", "_"))
        return repr(str(node).lower())

    def _translate_prop_name(self, node: Any) -> str:
        """Translate a ZIL P?NAME atom to a DjangoMOO property name string."""
        if isinstance(node, list) and node:
            node = node[0] if len(node) == 1 else node
        if isinstance(node, str):
            upper = node.upper()
            if upper in _PROP_MAP:
                return repr(_PROP_MAP[upper])
            if upper.startswith("P?"):
                return repr(upper[2:].lower().replace("-", "_"))
            return repr(upper.lower().replace("-", "_"))
        return repr(str(node).lower())


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def translate_routine(routine: ZilRoutine) -> str:
    """Translate a ZilRoutine to a complete verb file string."""
    return ZilTranslator(routine).translate()


def translate_m_clause(routine: ZilRoutine, m_constant: str) -> str:
    """Translate one M-* clause from an ACTION routine."""
    return ZilTranslator(routine).translate_m_clause(m_constant)


def has_m_dispatch(routine: ZilRoutine) -> bool:
    """Return True if routine dispatches on M-* constants."""
    return ZilTranslator(routine).has_m_dispatch()


def m_constants_found(routine: ZilRoutine) -> list[str]:
    """Return list of M-* constants handled by an ACTION routine."""
    return ZilTranslator(routine).m_constants_found()
