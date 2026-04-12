"""
Translate ZIL routine ASTs into DjangoMOO Python verb code.

Each ZilRoutine is compiled to the body of a DjangoMOO verb function:

    def verb(this, passthrough, _, *args, **kwargs):
        <translated body>

Translation is best-effort:  recognisable ZIL constructs become idiomatic
Python that calls the ``$zork_sdk`` component verbs via ``_.zork_sdk.*``.
Unrecognised constructs fall back to a ``# ZIL: ...`` comment followed by
``raise NotImplementedError(...)``.
"""

from __future__ import annotations

import textwrap
from typing import Any

from .ir import FLAG_PROPERTIES, ZIL_VERBS, ZilRoutine

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
    "PRSI": "context.parser.get_pobj('with')",
    "PRSA": "verb_name",
    "SCORE": "_.zork_sdk.zstate_get('SCORE')",
    "MOVES": "_.zork_sdk.zstate_get('MOVES')",
    "DEATHS": "_.zork_sdk.zstate_get('DEATHS')",
    "VERBOSE-MODE": "_.zork_sdk.zstate_get('VERBOSE-MODE')",
    "SUPERBRIEF": "_.zork_sdk.zstate_get('SUPERBRIEF')",
    "ROOMS": "_.zork_sdk.zstate_get('ROOMS')",
    "P-CONT": "context.player",
    "PLAYER": "context.player",
    "THIEF": 'lookup("thief")',
    "ROBBER": 'lookup("thief")',
    "CYCLOPS": 'lookup("cyclops")',
    "TROLL": 'lookup("troll")',
    "DEMON": 'lookup("demon")',
    "VAMPIRE": 'lookup("vampire bat")',
    "LIT-ROOM": "_.zork_sdk.zstate_get('LIT-ROOM')",
    "ENDGAME": "_.zork_sdk.zstate_get('ENDGAME')",
    "DEAD": "_.zork_sdk.zstate_get('DEAD')",
    "LUCKY": "_.zork_sdk.zstate_get('LUCKY')",
    "LAST-SCORE": "_.zork_sdk.zstate_get('LAST-SCORE')",
}

# ---------------------------------------------------------------------------
# ZIL action M-* constants
# ---------------------------------------------------------------------------

M_CLAUSES = {"M-LOOK", "M-BEG", "M-END", "M-ENTER", "M-LEAVE", "M-FLASH", "M-OBJDESC"}

_M_TO_VERB: dict[str, str] = {
    "M-LOOK": "look",
    "M-BEG": "confunc",
    "M-END": "exitfunc",
    "M-ENTER": "enterfunc",
    "M-LEAVE": "exitfunc",
}


# ---------------------------------------------------------------------------
# ZilTranslator
# ---------------------------------------------------------------------------


class ZilTranslator:
    """Translate a single ZilRoutine body into Python verb source."""

    def __init__(self, routine: ZilRoutine) -> None:
        self.routine = routine
        self._indent = 0
        self._lines: list[str] = []
        self._imports: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self) -> str:
        """Return the full verb file body as a string."""
        body_lines = self._translate_body(self.routine.body)
        imports = self._build_imports()
        header = self._shebang()
        parts = [header, "# pylint: disable=return-outside-function,undefined-variable"]
        if imports:
            parts.append(imports)
        parts.append(f"# ZIL routine: {self.routine.name}")
        if self.routine.params:
            parts.append(f"# params: {', '.join(self.routine.params)}")
        if self.routine.aux_vars:
            parts.append(f"# aux: {', '.join(self.routine.aux_vars)}")
        parts.append("")
        parts.extend(body_lines)
        return "\n".join(parts) + "\n"

    def translate_m_clause(self, m_constant: str) -> str:
        """
        Translate one M-* branch from an ACTION routine.

        Extracts the body of the COND clause matching m_constant.
        """
        clause_body = self._extract_m_clause(self.routine.body, m_constant)
        if clause_body is None:
            return f"# No {m_constant} clause found in {self.routine.name}\npass\n"
        body_lines = self._translate_body(clause_body)
        imports = self._build_imports()
        header = self._shebang_m(m_constant)
        parts = [header, "# pylint: disable=return-outside-function,undefined-variable"]
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
        return f"#!moo verb {name} --on $zork_thing"

    def _shebang_m(self, m_constant: str) -> str:
        verb = _M_TO_VERB.get(m_constant, m_constant.lower().replace("m-", ""))
        name = self.routine.name.lower().replace("_", "-")
        return f"#!moo verb {verb} --on ${name.replace('-', '_')}"

    # ------------------------------------------------------------------
    # Import bookkeeping
    # ------------------------------------------------------------------

    def _need_import(self, name: str) -> None:
        self._imports.add(name)

    def _build_imports(self) -> str:
        if not self._imports:
            return ""
        names = sorted(self._imports)
        return f"from moo.sdk import {', '.join(names)}"

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
            lines.append(" " * indent + "pass")
        return lines

    def _indent_str(self, indent: int) -> str:
        return "    " * indent

    def _translate_stmt(self, form: Any, indent: int = 0) -> list[str]:
        """Translate one form as a statement, returning lines."""
        ind = self._indent_str(indent)

        if form is None or (isinstance(form, list) and not form):
            return []

        if isinstance(form, (int, str)) and not isinstance(form, list):
            # Bare atom or number as statement — just evaluate
            expr = self._translate_expr(form)
            return [f"{ind}{expr}"]

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
            val = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}return {val}"]

        # --- output ---
        if head == "TELL":
            return [f"{ind}{self._translate_tell(form)}"]
        if head == "CRLF":
            return [f"{ind}print()"]
        if head == "PRINT":
            val = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}print({val})"]
        if head in ("PRINT-CR", "PRINTR"):
            val = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}print({val})"]

        # --- conditionals ---
        if head == "COND":
            return self._translate_cond(form, indent)
        if head == "AND":
            # as statement: evaluate left-to-right, stop on falsy
            parts = " and ".join(self._translate_expr(a) for a in form[1:])
            return [f"{ind}{parts}"]
        if head == "OR":
            parts = " or ".join(self._translate_expr(a) for a in form[1:])
            return [f"{ind}{parts}"]
        if head == "NOT":
            val = self._translate_expr(form[1]) if len(form) > 1 else "True"
            return [f"{ind}not {val}"]

        # --- loops ---
        if head == "REPEAT":
            body = list(form[2:]) if len(form) > 2 else list(form[1:])
            inner = self._translate_body(body, indent + 1)
            return [f"{ind}while True:"] + inner

        if head == "PROG":
            # (PROG () body...) — inline block
            body = list(form[2:]) if len(form) > 2 and isinstance(form[1], (list, tuple)) else list(form[1:])
            return self._translate_body(body, indent)

        if head == "MAP-CONTENTS":
            # (MAP-CONTENTS (var obj) body...)
            if len(form) > 2 and isinstance(form[1], (list, tuple)):
                var_list = form[1]
                var_name = str(var_list[0]).lower() if var_list else "item"
                container = self._translate_expr(var_list[1]) if len(var_list) > 1 else "this"
                body = list(form[2:])
                inner = self._translate_body(body, indent + 1)
                return [f"{ind}for {var_name} in {container}.contents.all():"] + inner
            return [f"{ind}# ZIL: {form!r}", f"{ind}raise NotImplementedError('MAP-CONTENTS not translated')"]

        # --- movement ---
        if head == "MOVE":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            dest = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}_.zork_sdk.move({obj}, {dest})"]
        if head in ("REMOVE", "REMOVE-CAREFULLY"):
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}_.zork_sdk.remove({obj})"]
        if head == "GOTO":
            room = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}_.zork_sdk.goto({room})"]
        if head == "DO-WALK":
            direction = self._translate_expr(form[1]) if len(form) > 1 else '"north"'
            return [f"{ind}_.zork_sdk.walk({direction})"]

        # --- flags ---
        if head == "FSET":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            flag = self._translate_flag_name(form[2]) if len(form) > 2 else '"unknown"'
            return [f"{ind}_.zork_sdk.set_flag({obj}, {flag}, True)"]
        if head == "FCLEAR":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            flag = self._translate_flag_name(form[2]) if len(form) > 2 else '"unknown"'
            return [f"{ind}_.zork_sdk.set_flag({obj}, {flag}, False)"]

        # --- properties ---
        if head == "PUTP":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            prop = self._translate_prop_name(form[2]) if len(form) > 2 else '"unknown"'
            val = self._translate_expr(form[3]) if len(form) > 3 else "None"
            return [f"{ind}{obj}.set_property({prop}, {val})"]

        # --- global state ---
        if head == "SETG":
            key = str(form[1]).upper() if len(form) > 1 else "UNKNOWN"
            val = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}_.zork_sdk.zstate_set({repr(key)}, {val})"]

        # --- score ---
        if head == "SCORE":
            delta = self._translate_expr(form[1]) if len(form) > 1 else "0"
            return [f"{ind}_.zork_sdk.score_update({delta})"]

        # --- death ---
        if head == "JIGS-UP":
            msg = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}_.zork_sdk.jigs_up({msg})"]

        # --- queue/interrupts ---
        if head == "ENABLE":
            inner = form[1] if len(form) > 1 else None
            if isinstance(inner, list) and inner and str(inner[0]).upper() == "QUEUE":
                routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                delay = self._translate_expr(inner[2]) if len(inner) > 2 else "1"
                return [f"{ind}_.zork_sdk.queue({routine}, {delay})"]
            return [f"{ind}# ZIL: {form!r}", f"{ind}raise NotImplementedError('ENABLE not translated')"]
        if head == "DISABLE":
            inner = form[1] if len(form) > 1 else None
            if isinstance(inner, list):
                routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                return [f"{ind}_.zork_sdk.cancel({routine})"]
            return [f"{ind}# ZIL: {form!r}", f"{ind}raise NotImplementedError('DISABLE not translated')"]

        # --- perform (indirect verb call) ---
        if head == "PERFORM":
            verb_atom = self._translate_expr(form[1]) if len(form) > 1 else '"unknown"'
            prso = self._translate_expr(form[2]) if len(form) > 2 else "None"
            prsi = self._translate_expr(form[3]) if len(form) > 3 else "None"
            return [f"{ind}_.zork_sdk.perform({verb_atom}, {prso}, {prsi})"]

        # --- local set ---
        if head == "SET":
            var = str(form[1]).lower() if len(form) > 1 else "_var"
            val = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}{var} = {val}"]

        # --- everything else: try as expression statement ---
        expr = self._translate_expr(form)
        if "NotImplementedError" in expr:
            comment = repr(form)[:120]
            return [
                f"{ind}# ZIL: {comment}",
                f"{ind}raise NotImplementedError({repr(str(form[0]))!r} + ' not yet translated')",
            ]
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
        if isinstance(node, str):
            # Atom or string literal
            if node.startswith('"') or (node and node[0].islower()):
                # Already decoded string from parser
                return repr(node)
            upper = node.upper()
            # T / FALSE
            if upper == "T":
                return "True"
            if upper == "FALSE" or upper == "<>":
                return "False"
            # Local variable reference (lowercase param/aux)
            if upper in (p.upper() for p in self.routine.params + self.routine.aux_vars):
                return upper.lower()
            return repr(node)

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

        # --- global variable dereference: ,NAME ---
        # In the parsed AST, ,NAME appears as a bare atom that was parsed as-is.
        # The ZIL comma prefix is lexed as part of the atom value by some parsers,
        # but our tokenizer treats it as a separate atom following a comma.
        # Since we parse comma as an atom char... actually our tokenizer doesn't.
        # ZIL ,VAR is a global reference; in the AST it comes through as the atom name.
        # We handle this by checking the head against known globals / ZIL object atoms.

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
        if head_upper in ("==", "EQUAL?", "=?"):
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
            return f"_.zork_sdk.flag({obj}, {flag})"

        # --- object containment / location ---
        if head_upper == "IN?":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            container = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"{obj}.location == {container}"
        if head_upper == "LOC":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f"{obj}.location"
        if head_upper in ("FIRST?", "FIRST"):
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f"next(iter({obj}.contents.all()), None)"
        if head_upper in ("NEXT?", "NEXT"):
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            # Note: ZIL linked-list traversal — use for-loop in real code
            return "None  # ZIL NEXT? linked-list; use contents.all() instead"
        if head_upper == "GLOBAL-IN?":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            loc = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"_.zork_sdk.global_in({obj}, {loc})"

        # --- properties ---
        if head_upper == "GETP":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            prop = self._translate_prop_name(node[2]) if len(node) > 2 else '"unknown"'
            return f"{obj}.get_property({prop})"
        if head_upper == "PUTP":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            prop = self._translate_prop_name(node[2]) if len(node) > 2 else '"unknown"'
            val = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"{obj}.set_property({prop}, {val})"

        # --- global state read ---
        if head_upper == "SETG":
            key = str(node[1]).upper() if len(node) > 1 else "UNKNOWN"
            val = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"_.zork_sdk.zstate_set({repr(key)}, {val})"
        if head_upper == "GVAL":
            key = str(node[1]).upper() if len(node) > 1 else "UNKNOWN"
            if key in _GLOBAL_MAP:
                return _GLOBAL_MAP[key]
            return f"_.zork_sdk.zstate_get({repr(key)})"

        # --- output ---
        if head_upper == "TELL":
            return self._translate_tell(node)
        if head_upper == "CRLF":
            return "print()"
        if head_upper in ("PRINT", "PRINTR", "PRINT-CR"):
            val = self._translate_expr(node[1]) if len(node) > 1 else '""'
            return f"print({val})"
        if head_upper == "PICK-ONE":
            table = self._translate_expr(node[1]) if len(node) > 1 else '"unknown"'
            return f"_.zork_sdk.pick({table})"

        # --- verb dispatch ---
        if head_upper == "VERB?":
            verbs = [str(v).upper() for v in node[1:] if isinstance(v, str)]
            aliases: list[str] = []
            for v in verbs:
                aliases.extend(ZIL_VERBS.get(v, [v.lower()]))
            return f"verb_name in {aliases!r}"

        # --- random ---
        if head_upper == "RANDOM":
            n = self._translate_expr(node[1]) if len(node) > 1 else "6"
            self._need_import("random")  # noqa: F821 — actually from moo.sdk, but random is allowed
            return f"random.randint(1, {n})"
        if head_upper == "PROB":
            n = self._translate_expr(node[1]) if len(node) > 1 else "50"
            return f"random.randint(1, 100) <= {n}"

        # --- score ---
        if head_upper == "SCORE":
            delta = self._translate_expr(node[1]) if len(node) > 1 else "0"
            return f"_.zork_sdk.score_update({delta})"

        # --- death ---
        if head_upper == "JIGS-UP":
            msg = self._translate_expr(node[1]) if len(node) > 1 else '""'
            return f"_.zork_sdk.jigs_up({msg})"

        # --- desc ---
        if head_upper in ("OBJECT-PNAME",):
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f"_.zork_sdk.desc({obj})"

        # --- perform ---
        if head_upper == "PERFORM":
            verb_atom = self._translate_expr(node[1]) if len(node) > 1 else '"unknown"'
            prso = self._translate_expr(node[2]) if len(node) > 2 else "None"
            prsi = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"_.zork_sdk.perform({verb_atom}, {prso}, {prsi})"

        # --- variable / global dereference by head alone ---
        # Some constructs like (,LAMP) are parsed as a list with one string element
        if len(node) == 1 and isinstance(node[0], str):
            atom = node[0].upper()
            if atom in _GLOBAL_MAP:
                return _GLOBAL_MAP[atom]
            # Object reference: look up by name
            obj_name = atom.lower().replace("-", " ")
            return f'lookup("{obj_name}")'

        # Bare atom references that appear as the head with no args
        if head_upper in _GLOBAL_MAP:
            return _GLOBAL_MAP[head_upper]

        # Routine call (another ZIL function)
        if head_upper[0].isalpha() and not head_upper.startswith("V?"):
            func_name = head_upper.lower().replace("-", "_")
            args = ", ".join(self._translate_expr(a) for a in node[1:])
            # Check if this is a known SDK call
            return f"{func_name}({args})  # ZIL routine call"

        # Fallback
        comment = repr(node)[:80]
        return f"None  # ZIL: {comment}"

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
                    segments.append(f"_.zork_sdk.desc({obj})")
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

    def _translate_cond(self, form: list, indent: int) -> list[str]:
        """Translate <COND (cond body...) (cond body...) (T body...)>."""
        ind = self._indent_str(indent)
        lines = []
        clauses = form[1:]

        for i, clause in enumerate(clauses):
            if not isinstance(clause, (list, tuple)) or not clause:
                continue
            cond = clause[0]
            body = list(clause[1:])

            # T / ELSE clause
            is_else = isinstance(cond, str) and cond.upper() in ("T", "ELSE")

            if is_else:
                lines.append(f"{ind}else:")
            elif i == 0:
                cond_expr = self._translate_expr(cond)
                lines.append(f"{ind}if {cond_expr}:")
            else:
                cond_expr = self._translate_expr(cond)
                lines.append(f"{ind}elif {cond_expr}:")

            if body:
                body_lines = self._translate_body(body, indent + 1)
                lines.extend(body_lines)
            else:
                lines.append(f"{ind}    pass")

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
