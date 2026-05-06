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


def _verb_attr_safe(name: str) -> bool:
    """True when a verb name can be invoked via attribute access.

    DjangoMOO's Object.__getattr__ resolves dotted access to verb dispatch,
    but only when the name is a valid Python identifier (no hyphens, no
    leading digits, not a keyword).  Hyphenated names (``i-river``,
    ``v-take``) must keep using ``invoke_verb``.
    """
    return name.isidentifier() and name not in _PY_KEYWORDS


def _predicate_python_name(zil_name: str) -> str | None:
    """For a ZIL ``?``-suffixed predicate atom (e.g. ``ACCESSIBLE?``,
    ``FOREST-ROOM?``), return the dot-syntax-friendly Python name
    (``is_accessible``, ``is_forest_room``).  Returns ``None`` when the
    name isn't a user-defined predicate (no ``?`` suffix, or a built-in
    operator like ``EQUAL?`` / ``IN?`` / ``0?`` handled by other rules).
    """
    if not zil_name.endswith("?"):
        return None
    base = zil_name[:-1]
    if not base or not base[0].isalpha():
        return None
    snake = base.lower().replace("-", "_")
    return f"is_{snake}"


def _routine_dot_name(zil_name: str) -> str | None:
    """Return the Python attribute-safe name for invoking a ZIL routine
    via dot-syntax (``_.zork_thing.<name>(...)``), or ``None`` when no
    safe form exists.

    Drops the ``v-`` substrate prefix, snake-cases hyphenated names
    (D-mild), and routes ``?``-suffixed predicates through
    ``_predicate_python_name``.  Returns ``None`` for names that would
    still collide with a Python keyword or contain non-identifier
    characters after rewriting — those callers fall back to
    ``invoke_verb``.
    """
    pred = _predicate_python_name(zil_name)
    if pred is not None:
        return pred
    name = zil_name.lower()
    if name.startswith("v-"):
        name = name[2:]
    snake = name.replace("-", "_")
    if _verb_attr_safe(snake):
        return snake
    return None


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

# P? direction-token atoms.  ZIL stores direction codes in PRSO when the
# player types ``go east`` etc., and routines compare PRSO against these
# atoms to decide whether to allow movement.  In DjangoMOO the direction
# is the dobj *string*, not an Object — so an ``EQUAL? ,PRSO ,P?EAST``
# clause becomes ``context.parser.get_dobj_str() == "east"``.
_DIRECTION_ATOMS: dict[str, str] = {
    "P?LAND": "land",
    "P?NORTH": "north",
    "P?SOUTH": "south",
    "P?EAST": "east",
    "P?WEST": "west",
    "P?UP": "up",
    "P?DOWN": "down",
    "P?NE": "ne",
    "P?NW": "nw",
    "P?SE": "se",
    "P?SW": "sw",
    "P?IN": "in",
    "P?OUT": "out",
}


_PROP_MAP: dict[str, str] = {
    "P?LDESC": "description",
    "P?FDESC": "description",
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
    "HERE": "context.player.here()",
    "PRSO": "context.parser.get_dobj()",
    "PRSI": "(context.parser.get_iobj() if context.parser.has_iobj() else None)",
    "PRSA": "verb_name",
    # F.3: ZIL parser-state globals — synonyms for the live PRSO/PRSI in
    # DjangoMOO since we don't keep a separate "last parsed" cache.
    "P-PRSO": "context.parser.get_dobj()",
    "P-PRSI": "(context.parser.get_iobj() if context.parser.has_iobj() else None)",
    "SCORE": "context.player.zstate_get('SCORE')",
    "MOVES": "context.player.zstate_get('MOVES')",
    "DEATHS": "context.player.zstate_get('DEATHS')",
    "VERBOSE-MODE": "context.player.zstate_get('VERBOSE-MODE')",
    "SUPERBRIEF": "context.player.zstate_get('SUPERBRIEF')",
    "ROOMS": "context.player.zstate_get('ROOMS')",
    "P-CONT": "context.player",
    "PLAYER": "context.player",
    "THIEF": 'lookup("thief")',
    "ROBBER": 'lookup("thief")',
    "CYCLOPS": 'lookup("cyclops")',
    "TROLL": 'lookup("troll")',
    "DEMON": 'lookup("demon")',
    "VAMPIRE": 'lookup("vampire bat")',
    "LIT-ROOM": "context.player.zstate_get('LIT-ROOM')",
    "ENDGAME": "context.player.zstate_get('ENDGAME')",
    "DEAD": "context.player.zstate_get('DEAD')",
    "LUCKY": "context.player.zstate_get('LUCKY')",
    "LAST-SCORE": "context.player.zstate_get('LAST-SCORE')",
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
    "M-BEG": "preturnfunc",
    "M-END": "turnfunc",
    "M-ENTER": "enterfunc",
    "M-LEAVE": "exitfunc",
    # M-FLASH ("you've been here before") and M-OBJDESC ("describe object")
    # don't have widely-used clauses but APPLY may invoke them on objects
    # that have no handler — the has_verb guard makes those calls a no-op.
    "M-FLASH": "flashfunc",
    "M-OBJDESC": "descfunc",
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
        owner_overrides: dict[str, str] | None = None,
        pre_handler_routines: set[str] | None = None,
        display_names: dict[str, str] | None = None,
        substrate_display_names: dict[str, str] | None = None,
        routine_to_verbs: dict[str, list[str]] | None = None,
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
        # Per-routine ``--on $<owner>`` shebang overrides (uppercase routine
        # name → owner property name without the ``$``).  D3 Phase 1 +
        # syntax-finish bucket B use this to relocate 0-OBJECT-only and
        # same-routine mixed-arity substrate verbs onto ``$player``.
        self.owner_overrides: dict[str, str] = owner_overrides or {}
        # V-routine names (uppercase) whose ``PRE-X`` handler exists and
        # should be invoked at the top of the substrate body
        # (syntax-finish bucket A).
        self.pre_handler_routines: set[str] = pre_handler_routines or set()
        # Atom → globally-unique display name (e.g. ``"WHITE-HOUSE"`` →
        # ``"white house"``).  Used to emit ``--on "<display>"`` shebangs
        # that resolve at verb-load time without polluting the System
        # Object with per-object atom aliases.
        self.display_names: dict[str, str] = display_names or {}
        # Substrate parent class snake-name → display name (e.g.
        # ``"zork_thing"`` → ``"Zork Thing"``).  Honoured by ``_shebang``
        # when ``owner_overrides`` resolves to a substrate handle.
        self.substrate_display_names: dict[str, str] = substrate_display_names or {}
        # V-routine name (uppercase) → list of player verbs that dispatch
        # to it via ZIL SYNTAX rules.  ``_shebang`` uses this to register
        # the substrate verb under the names a player actually types
        # (``light`` for V-LAMP-ON), with the routine name as a fallback
        # alias when no SYNTAX rule mentions the routine.
        self.routine_to_verbs: dict[str, list[str]] = routine_to_verbs or {}
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
        # True while ``translate_m_clause`` is rendering a body.  PRSA
        # references inside an M-clause resolve to ``the_player_verb``
        # (the do_command-supplied verb word) instead of ``player_verb``
        # (which equals the invoked verb name = "preturnfunc" at that
        # point in dispatch).
        self._in_m_clause = False

    def _is_noop_body(self, forms: list) -> bool:
        """Return True when an M-clause body is effectively a no-op.

        ZIL's ``<COND (<EQUAL? .RARG ,M-LOOK> <>)>`` says "for look,
        return FALSE so default behavior continues."  Emitting an empty
        verb on the object would override normal dispatch via
        last-match-wins.  Detect bare ``<>`` (None / FALSE) and bare
        ``RTRUE`` / ``RFALSE`` so the caller can skip emission."""
        if not isinstance(forms, list):
            return forms is None
        if not forms:
            return True
        if len(forms) > 1:
            return False
        only = forms[0]
        if only is None:
            return True
        if isinstance(only, str):
            upper = only.upper()
            return upper in ("RTRUE", "RFALSE", "T", "<>", "FALSE")
        if isinstance(only, list) and only:
            head = only[0]
            if isinstance(head, str) and head.upper() in ("RTRUE", "RFALSE", "RETURN"):
                return True
        return False

    def _is_prso_atom(self, node) -> bool:
        """Return True if ``node`` is a ZIL ``,PRSO`` reference (the parser
        keeps the comma as part of the atom token)."""
        return isinstance(node, str) and node.lstrip(",.").upper() == "PRSO"

    def _direction_string(self, node) -> str | None:
        """If ``node`` is a ``,P?<DIRECTION>`` ref, return the direction string;
        otherwise None.  Used by the EQUAL? handler to detect direction-token
        comparisons that should map to ``get_dobj_str() == "east"`` etc."""
        if isinstance(node, str):
            atom = node.lstrip(",.").upper()
            return _DIRECTION_ATOMS.get(atom)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _is_m_clause_test(self, test) -> bool:
        """Return True if a COND clause test is ``<EQUAL? .RARG ,M-X ...>``.

        Identifies clauses that handle ZIL lifecycle events (M-BEG, M-END,
        M-LOOK, etc.).  These are split out into separate verb files via
        ``translate_m_clause`` and don't fire on normal verb dispatch
        (rarg=None), so the full-routine emit can prune them.
        """
        if not isinstance(test, list) or len(test) < 3:
            return False
        head = test[0]
        if not isinstance(head, str) or head.upper() not in ("EQUAL?", "==?", "=?", "=="):
            return False
        arg1 = test[1]
        if not isinstance(arg1, str) or arg1.lstrip(",.").upper() != "RARG":
            return False
        for arg in test[2:]:
            if not isinstance(arg, str):
                return False
            if arg.lstrip(",.").upper() not in M_CLAUSES:
                return False
        return True

    def _is_verb_clause_test(self, test) -> bool:
        """Return True if a COND clause test is dispatched on player verb.

        Recognises ``<VERB? X Y>`` and ``<AND <VERB? X> ...other...>``.
        These clauses are split out into per-clause verb files so the parser
        does natural dispatch instead of an ``if player_verb in [...]``
        switch inside one god-verb.
        """
        if not isinstance(test, list) or not test:
            return False
        head = test[0]
        if not isinstance(head, str):
            return False
        upper = head.upper()
        if upper == "VERB?":
            return True
        if upper == "AND":
            for sub in test[1:]:
                if isinstance(sub, list) and sub and isinstance(sub[0], str) and sub[0].upper() == "VERB?":
                    return True
        return False

    def _verbs_in_test(self, test) -> list[str]:
        """Extract verb atoms from a ``<VERB? X Y>`` or ``<AND <VERB? X> ...>``."""
        if not isinstance(test, list) or not test:
            return []
        head = str(test[0]).upper()
        if head == "VERB?":
            return [str(v).upper() for v in test[1:] if isinstance(v, str)]
        if head == "AND":
            for sub in test[1:]:
                if isinstance(sub, list) and sub and isinstance(sub[0], str) and sub[0].upper() == "VERB?":
                    return [str(v).upper() for v in sub[1:] if isinstance(v, str)]
        return []

    def _extra_test_in_and(self, test) -> list | None:
        """For ``<AND <VERB? X> <other> ...>`` return ``<AND <other> ...>`` or
        the single remaining test.  Returns None if there's no extra test
        (i.e. the input was a bare ``<VERB? X>`` or AND with only the VERB?)."""
        if not isinstance(test, list) or not test or str(test[0]).upper() != "AND":
            return None
        extras = [
            sub
            for sub in test[1:]
            if not (isinstance(sub, list) and sub and isinstance(sub[0], str) and sub[0].upper() == "VERB?")
        ]
        if not extras:
            return None
        if len(extras) == 1:
            return extras[0]
        return ["AND", *extras]

    def _prune_m_clauses_in_forms(self, forms: list) -> list:
        """Remove M-* lifecycle clauses from any top-level COND in ``forms``.

        ZIL OBJECT-FUNCTION routines wrap M-* dispatch and player-verb
        dispatch in a single COND.  After ``translate_m_clause`` emits the
        M-* branches as separate verb files, the residual full-routine
        body should drop those branches so it doesn't carry dead lifecycle
        code (and the rarg=None fast-path doesn't waste cycles checking
        ``rarg in (M-ENTER, M-END, M-LOOK)``).
        """
        if not isinstance(forms, list):
            return forms
        result = []
        for form in forms:
            if isinstance(form, list) and form and isinstance(form[0], str) and form[0].upper() == "COND":
                head = form[0]
                kept = [head]
                any_dropped = False
                for clause in form[1:]:
                    if not isinstance(clause, (list, tuple)) or not clause:
                        kept.append(clause)
                        continue
                    if self._is_m_clause_test(clause[0]):
                        any_dropped = True
                        continue
                    kept.append(clause)
                if any_dropped and len(kept) == 1:
                    # The whole COND was just M-* clauses — drop it entirely.
                    continue
                result.append(kept)
            else:
                result.append(form)
        return result

    def _find_verb_dispatch(self, forms: list) -> list | None:
        """Find a top-level COND that has at least one VERB? clause.

        Mirrors ``_find_m_dispatch`` for verb-based dispatch.
        """
        for form in forms:
            if not isinstance(form, list) or not form:
                continue
            if str(form[0]).upper() != "COND":
                continue
            for clause in form[1:]:
                if not isinstance(clause, (list, tuple)) or not clause:
                    continue
                if self._is_verb_clause_test(clause[0]):
                    return form
        return None

    def _verb_clauses(self, forms: list) -> list[tuple[list[str], list, list]]:
        """Iterate VERB? clauses in the routine body's top-level COND.

        Returns ``(verb_atoms, extra_test_or_None, body_forms)`` per clause.
        """
        dispatch = self._find_verb_dispatch(forms)
        if dispatch is None:
            return []
        out: list[tuple[list[str], list, list]] = []
        for clause in dispatch[1:]:
            if not isinstance(clause, (list, tuple)) or not clause:
                continue
            test = clause[0]
            if not self._is_verb_clause_test(test):
                continue
            verbs = self._verbs_in_test(test)
            if not verbs:
                continue
            extra = self._extra_test_in_and(test)
            body = list(clause[1:])
            out.append((verbs, extra, body))
        return out

    def _prune_verb_clauses_in_forms(self, forms: list) -> list:
        """Remove VERB?-tested clauses from any top-level COND in ``forms``.

        Counterpart to ``_prune_m_clauses_in_forms``; preserves T/ELSE
        defaults and other non-VERB? clauses on the residual.

        A.5: when the residual COND collapses to a single ``(T body)`` /
        ``(ELSE body)`` clause, unwrap it to the bare body forms so the
        translator emits the body directly instead of an awkward
        ``if True: ...`` wrapper.
        """
        if not isinstance(forms, list):
            return forms
        result = []
        for form in forms:
            if isinstance(form, list) and form and isinstance(form[0], str) and form[0].upper() == "COND":
                head = form[0]
                kept = [head]
                any_dropped = False
                for clause in form[1:]:
                    if not isinstance(clause, (list, tuple)) or not clause:
                        kept.append(clause)
                        continue
                    if self._is_verb_clause_test(clause[0]):
                        any_dropped = True
                        continue
                    kept.append(clause)
                if any_dropped and len(kept) == 1:
                    continue
                # A.5: if only one clause remains and its test is T/ELSE,
                # inline the body forms — the COND wrapper is dead weight.
                if any_dropped and len(kept) == 2:
                    only_clause = kept[1]
                    if isinstance(only_clause, (list, tuple)) and only_clause:
                        test = only_clause[0]
                        if isinstance(test, str) and test.upper() in ("T", "ELSE"):
                            result.extend(list(only_clause[1:]))
                            continue
                result.append(kept)
            else:
                result.append(form)
        return result

    def translate(self) -> str:
        """Return the full verb file body, or the empty string when the
        residual is a no-op (so the generator can skip emission)."""
        # When this routine has M-* lifecycle or VERB? dispatch, those
        # branches are emitted as separate verb files (``translate_m_clause``
        # / ``translate_verb_clause``).  Prune them from the full-routine
        # body so the residual god-verb only carries any catch-all (T/ELSE)
        # behaviour and non-VERB? helpers.
        body_forms = self.routine.body
        any_pruned = False
        if self.has_m_dispatch():
            body_forms = self._prune_m_clauses_in_forms(body_forms)
            any_pruned = True
        if self.action_owner and self._find_verb_dispatch(body_forms) is not None:
            body_forms = self._prune_verb_clauses_in_forms(body_forms)
            any_pruned = True
        # If pruning leaves an empty body, skip emission — the per-clause
        # files cover everything and substrate verbs handle the rest via
        # natural parser dispatch.
        if any_pruned and self._is_noop_body(body_forms):
            return ""
        # Reset _verbs_handled so the residual shebang reflects only verbs
        # the residual body still references (after pruning).
        self._verbs_handled = set()
        body_lines = self._translate_body(body_forms)

        # A.4: skip emission when pruning M-/VERB?-clauses leaves a body
        # with no semantic content (empty, comments-only, or all-``pass``).
        # Routines with ONLY M-* clauses (no VERB?) end up with just the
        # param/aux unpacks + ``pass``; the per-clause files cover them.
        # Skip only when something was actually pruned — preserves the
        # legitimate "comment-only" output of unhandled-form fallbacks
        # (e.g. ``<ENABLE <SOMETHING-NOT-QUEUE>>`` in test_translator).
        def _is_semantically_empty(lines: list[str]) -> bool:
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped == "pass":
                    continue
                return False
            return True

        if any_pruned and _is_semantically_empty(body_lines):
            return ""
        # Make ZIL's implicit-return-of-last-expression explicit.
        body_lines = self._wrap_trailing_return_recursive(body_lines, 0)
        # Per-action-owner residuals (the "leftovers" after VERB? clauses are
        # split into separate files) also need a ``passthrough()`` at the end
        # so unhandled fall-off invokes the substrate verb on the parent class.
        # Without this, an action_owner verb like trap_door's residual that
        # only handles the CELLAR branch falls off silently in LIVING-ROOM
        # — masking the per-clause Living-Room split because the residual's
        # PK is lower (loaded first → wins same-rank tie in parser dispatch).
        if self.action_owner and any_pruned:
            body_lines.append("return passthrough()")
        # syntax-finish bucket A: inline pre-X check at top of substrate body
        # for V-routines whose PRE-X handler exists.  Replaces the old
        # syntax/ trampoline that fired pre-X before the substrate.
        if self.routine.name.upper() in self.pre_handler_routines:
            base = self.routine.name.lower().removeprefix("v-")
            # RestrictedPython rejects identifiers starting with ``_``, so the
            # local has to be a plain name (not ``_pre``).
            pre_lines = [
                f'pre_x = "pre-{base}"',
                "if _.zork_thing.has_verb(pre_x) and _.zork_thing.invoke_verb(pre_x):",
                "    return",
            ]
            body_lines = pre_lines + body_lines
        # Build param/aux unpack lines first so auto-import can scan their
        # default expressions too — `lookup("trophy_case")` may live there
        # rather than in the body proper.
        unpack_lines: list[str] = []
        for i, param in enumerate(self.routine.params):
            default = self.routine.initial_values.get(param)
            default_expr = self._translate_expr(default) if default is not None else "None"
            unpack_lines.append(f"{_sanitize_ident(param)} = args[{i}] if len(args) > {i} else {default_expr}")
        for aux in self.routine.aux_vars:
            default = self.routine.initial_values.get(aux)
            default_expr = self._translate_expr(default) if default is not None else "None"
            unpack_lines.append(f"{_sanitize_ident(aux)} = {default_expr}")
        body_lines, unpack_lines = self._polish(body_lines, unpack_lines)
        # If the residual body has any <VERB?> check, bind ``the_player_verb``
        # from the parser so it works even when this routine is invoked as a
        # sub-call from another verb (where the callee's ``verb_name`` is
        # its own routine name, not the player's typed verb).  The M-clause
        # path (``translate_m_clause``) binds ``the_player_verb`` from
        # ``args[1]`` instead — see that method.
        if self._verbs_handled:
            unpack_lines.append(
                "the_player_verb = (context.parser.words[0].lower() "
                "if context.parser is not None and context.parser.words "
                "else verb_name)"
            )
        self._auto_import(unpack_lines + body_lines)
        imports = self._build_imports()
        header = self._shebang()
        parts = [
            header,
            "# Generated by extras/zil_import — do not edit by hand",
            "# pylint: disable=return-outside-function,undefined-variable,pointless-statement,unnecessary-negation,disallowed-name,using-constant-test,redefined-outer-name,no-else-return,unused-variable,redefined-builtin,singleton-comparison,unnecessary-pass,expression-not-assigned",
            "",
        ]
        if imports:
            parts.append(imports)
        parts.append(f"# ZIL routine: {self.routine.name}")
        if self.routine.params:
            parts.append(f"# params: {', '.join(self.routine.params)}")
        if self.routine.aux_vars:
            parts.append(f"# aux: {', '.join(self.routine.aux_vars)}")
        parts.append("")
        parts.extend(unpack_lines)
        if unpack_lines:
            parts.append("")
        parts.extend(body_lines)
        return "\n".join(parts) + "\n"

    def translate_m_clause(self, m_constant: str) -> str:
        """Translate one M-* branch from an ACTION routine, returning the
        clause body as a complete verb file.  Returns the empty string when
        the body is a no-op (just ``<>`` / RFALSE / RTRUE) — caller skips
        emission so the substrate verb (e.g. ``v-look``) gets a chance to
        run via normal parser dispatch instead of being overridden by an
        empty stub."""
        clause_body = self._extract_m_clause(self.routine.body, m_constant)
        if clause_body is None:
            return f"# No {m_constant} clause found in {self.routine.name}\npass\n"
        if self._is_noop_body(clause_body):
            return ""
        # PRSA inside an M-clause should resolve to the ``args[1]``
        # passed by ``system/do_command.py`` — the player's typed verb
        # word — instead of ``player_verb`` (which equals the invoked
        # verb name "preturnfunc" at do_command time).  Toggle the flag
        # during body translation so ``_translate_expr`` does the swap.
        self._in_m_clause = True
        try:
            body_lines = self._translate_body(clause_body)
        finally:
            self._in_m_clause = False
        # Build param/aux unpack lines first so auto-import sees default exprs.
        unpack_lines: list[str] = []
        for i, param in enumerate(self.routine.params):
            default = self.routine.initial_values.get(param)
            if default is not None:
                default_expr = self._translate_expr(default)
            else:
                default_expr = f'"{m_constant}"'
            unpack_lines.append(f"{_sanitize_ident(param)} = args[{i}] if len(args) > {i} else {default_expr}")
        for aux in self.routine.aux_vars:
            default = self.routine.initial_values.get(aux)
            default_expr = self._translate_expr(default) if default is not None else "None"
            unpack_lines.append(f"{_sanitize_ident(aux)} = {default_expr}")
        # do_command passes the player's typed verb as args[1] (so PRSA
        # resolves correctly inside M-clauses).  Bind it for body refs.
        unpack_lines.append("the_player_verb = args[1] if len(args) > 1 else verb_name")
        body_lines, unpack_lines = self._polish(body_lines, unpack_lines)
        self._auto_import(unpack_lines + body_lines)
        imports = self._build_imports()
        header = self._shebang_m(m_constant)
        parts = [
            header,
            "# Generated by extras/zil_import — do not edit by hand",
            "# pylint: disable=return-outside-function,undefined-variable,pointless-statement,unnecessary-negation,disallowed-name,using-constant-test,redefined-outer-name,no-else-return,unused-variable,redefined-builtin,singleton-comparison,unnecessary-pass,expression-not-assigned",
        ]
        if imports:
            parts.append(imports)
        parts.append(f"# ZIL: {self.routine.name} / {m_constant}")
        parts.append("")
        parts.extend(unpack_lines)
        if unpack_lines:
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

    def has_verb_dispatch(self) -> bool:
        """Return True if the routine has a top-level COND with VERB? clauses
        suitable for per-clause split.  Only meaningful for routines with an
        ``action_owner`` (object/room ACTION handlers); global helpers don't
        get split."""
        if not self.action_owner:
            return False
        return self._find_verb_dispatch(self.routine.body) is not None

    def verb_clauses_for_split(self) -> list[tuple[list[str], list, list]]:
        """Return the VERB? clauses to emit as separate per-clause files.

        Each item is ``(verb_atoms, extra_test_or_None, body_forms)``.  Only
        meaningful when ``has_verb_dispatch()`` is True.
        """
        return self._verb_clauses(self.routine.body)

    def translate_verb_clause(self, verb_atoms: list[str], extra_test, body_forms: list) -> str:
        """Translate one VERB? clause as a complete verb file body."""
        if self._is_noop_body(body_forms):
            return ""
        # Emit the clause body, optionally wrapped in ``if <extra_test>:``
        # when the original ZIL clause was ``<AND <VERB? X> <other>>``.
        if extra_test is not None:
            wrapped_cond = ["COND", [extra_test, *body_forms]]
            body_lines = self._translate_body([wrapped_cond])
        else:
            body_lines = self._translate_body(body_forms)
        body_lines = self._wrap_trailing_return_recursive(body_lines, 0)
        # ZIL action handlers fall through to the V-routine when they end
        # without an explicit return (the routine's last expression
        # implicitly returned False).  In DjangoMOO that's a passthrough
        # to the substrate verb on the parent class — append it once at
        # the end so the unhandled tail of (e.g.) ``rope.take`` invokes
        # ``Zork Thing.take``.  Earlier ``return``/``return True`` paths
        # short-circuit this naturally.
        if self.action_owner:
            body_lines.append("return passthrough()")

        unpack_lines: list[str] = []
        for i, param in enumerate(self.routine.params):
            default = self.routine.initial_values.get(param)
            default_expr = self._translate_expr(default) if default is not None else "None"
            unpack_lines.append(f"{_sanitize_ident(param)} = args[{i}] if len(args) > {i} else {default_expr}")
        for aux in self.routine.aux_vars:
            default = self.routine.initial_values.get(aux)
            default_expr = self._translate_expr(default) if default is not None else "None"
            unpack_lines.append(f"{_sanitize_ident(aux)} = {default_expr}")

        body_lines, unpack_lines = self._polish(body_lines, unpack_lines)
        # Bind ``the_player_verb`` if any nested <VERB?> survived the split.
        # In a verb-dispatch clause, ``verb_name`` is normally the player verb
        # already, but a nested call into a helper routine (e.g. open_close)
        # may need the parser-derived value too.
        if self._verbs_handled:
            unpack_lines.append(
                "the_player_verb = (context.parser.words[0].lower() "
                "if context.parser is not None and context.parser.words "
                "else verb_name)"
            )
        self._auto_import(unpack_lines + body_lines)
        imports = self._build_imports()
        header = self._shebang_verb(verb_atoms)
        parts = [
            header,
            "# Generated by extras/zil_import — do not edit by hand",
            "# pylint: disable=return-outside-function,undefined-variable,pointless-statement,unnecessary-negation,disallowed-name,using-constant-test,redefined-outer-name,no-else-return,unused-variable,redefined-builtin,singleton-comparison",
            "",
        ]
        if imports:
            parts.append(imports)
        verb_label = "/".join(v.lower() for v in verb_atoms)
        parts.append(f"# ZIL routine: {self.routine.name} ({verb_label} branch)")
        parts.append("")
        parts.extend(unpack_lines)
        if unpack_lines:
            parts.append("")
        parts.extend(body_lines)
        return "\n".join(parts) + "\n"

    # ------------------------------------------------------------------
    # Shebang generation
    # ------------------------------------------------------------------

    # ZIL routine names that conflict with DjangoMOO built-in verbs.
    # These are game-initialization routines never intended as player commands.
    _SHEBANG_NAME_OVERRIDE: dict[str, str] = {
        "go": "_go",  # ZIL entry-point routine; conflicts with movement verb
    }

    def _on_for_substrate(self, owner_key: str) -> str:
        """Render a ``--on`` clause for a substrate parent class.

        Looks up the snake-name (``zork_thing``) in ``substrate_display_names``
        and emits a quoted display-name form (``--on "Zork Thing"``).  Falls
        back to ``$<owner_key>`` only if no display name was supplied — that
        path keeps the legacy alias-via-System-Object resolution path alive
        for callers that haven't been wired through.
        """
        display = self.substrate_display_names.get(owner_key)
        if display is not None:
            return f'--on "{display}"'
        return f"--on ${owner_key}"

    def _on_for_atom(self, atom: str) -> str:
        """Render a ``--on`` clause for a per-object/per-room handler.

        Uses the dataset-wide unique display name when available so the
        bootstrap loader resolves the verb to a single Object via
        ``Object.objects.filter(name__iexact=...)``.  Falls back to the
        atom's snake-form (``$west_house``) for atoms missing a display
        mapping — that branch shouldn't be hit once display_names is
        populated for every room/object.
        """
        display = self.display_names.get(atom)
        if display is not None:
            return f'--on "{display}"'
        return f"--on ${atom.lower().replace('-', '_')}"

    def _shebang_verb(self, verb_atoms: list[str]) -> str:
        """Shebang for a per-clause verb file.  Expands ZIL atoms to player
        synonyms via ``ZIL_VERBS`` so e.g. ATTACK becomes ``attack kill hit
        fight stab cut slice mung destroy break smash crack``."""
        aliases: list[str] = []
        seen: set[str] = set()
        for atom in verb_atoms:
            for alias in ZIL_VERBS.get(atom.upper(), [atom.lower()]):
                if alias not in seen:
                    aliases.append(alias)
                    seen.add(alias)
        verbs = " ".join(aliases)
        if self.action_owner:
            atom, _is_room = self.action_owner
            return f"#!moo verb {verbs} {self._on_for_atom(atom)} --dspec either"
        # Orphan per-clause split: no action owner means no target object.
        # Legacy code aimed at ``${routine_name}`` which is not a real
        # Object; leave that path on the substrate so it at least dispatches
        # off ``$zork_thing`` instead of vanishing.
        return f"#!moo verb {verbs} {self._on_for_substrate('zork_thing')} --dspec either"

    def _shebang(self) -> str:
        name = self.routine.name.lower().replace("_", "-")
        if self.action_owner and self._verbs_handled:
            atom, _is_room = self.action_owner
            verbs = " ".join(sorted(self._verbs_handled))
            return f"#!moo verb {verbs} {self._on_for_atom(atom)} --dspec either"
        name = self._SHEBANG_NAME_OVERRIDE.get(name, name)
        # Drop ``v-`` prefix on substrate V-routines so the parser finds
        # them by the natural verb name (last-match-wins on dobj routes
        # ``take leaflet`` to ``leaflet.take``, which inherits the
        # substrate body from ``$zork_thing``).
        if name.startswith("v-"):
            name = name[2:]
        # E + D-mild: rename ?-suffixed predicates to ``is_<base>`` and
        # snake-case hyphenated helper routines so callers reach them via
        # dot-syntax (``obj.is_accessible()`` / ``_.zork_thing.this_is_it``)
        # instead of always going through ``invoke_verb``.  Only applied
        # to non-action-owner routines; player-typed verbs with hyphens
        # (``put-on``, ``climb-down``) are kept as-is in the action-owner
        # branch above.
        dot_name = _routine_dot_name(self.routine.name)
        if dot_name is not None:
            name = dot_name
        # Honour D3 Phase 1 owner overrides: a 0-OBJECT-only substrate verb
        # (or same-routine mixed-arity) gets relocated from ``zork_thing``
        # to the actor class so parser dispatch finds it without going
        # through a syntax/ trampoline.
        owner = self.owner_overrides.get(self.routine.name.upper(), "zork_thing")
        # Substrate routines living on ``zork_thing`` are 1+ OBJECT verbs
        # invoked through dobj inheritance — ``--dspec this`` matches when
        # the parsed dobj is_a ``Zork Thing``.  Routines relocated to the
        # actor class are mixed-arity (or strictly 0-OBJECT); ``--dspec
        # either`` lets them fire with or without a dobj.  Without an
        # explicit dspec, argparse defaults to ``none`` and the parser
        # rejects every dobj-bearing sentence — V-TAKE, V-OPEN, etc. would
        # never match a real player command.
        dspec = "this" if owner == "zork_thing" else "either"
        return f"#!moo verb {name} {self._on_for_substrate(owner)} --dspec {dspec}"

    def _shebang_m(self, m_constant: str) -> str:
        """M-clause splits attach to the routine's action_owner room.

        The previous fallback used ``${routine_name}`` (e.g.
        ``$living_room_fcn``) — an object that doesn't exist, so the verb
        never reached its target room.  When ``action_owner`` is present
        we resolve to the actual room (``"living room"``); for orphan
        routines (no action_owner) we fall back to the substrate so the
        verb at least dispatches off ``$zork_thing``.
        """
        verb = _M_TO_VERB.get(m_constant, m_constant.lower().replace("m-", ""))
        # M-clauses are dispatched via the action_owner's class path, often
        # with no parsed dobj (M-BEG/M-LOOK fire from goto/look without one).
        # ``--dspec either`` keeps them fireable with or without a dobj.
        if self.action_owner:
            atom, _is_room = self.action_owner
            return f"#!moo verb {verb} {self._on_for_atom(atom)} --dspec either"
        return f"#!moo verb {verb} {self._on_for_substrate('zork_thing')} --dspec either"

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
        """Scan generated body lines and re-derive the import set from
        scratch.  Resetting (rather than only adding) ensures imports
        added by earlier translation paths are pruned when the polish
        pass removes the line that justified them — e.g. a ``lookup(``
        call rewritten away during polish should drop the ``lookup``
        import so the file doesn't carry an unused name."""
        # Strip ``# ...`` line comments so a primitive token in a
        # documentation comment doesn't keep an import alive.
        body = re.sub(r"#.*", "", "\n".join(lines))
        self._imports = set()
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
            # ZIL semantic: ``<RFALSE>`` inside an ACTION routine means
            # "I didn't handle this verb — fall through to standard
            # V-<verb> dispatch."  In DjangoMOO that's the inheritance
            # passthrough: the per-object verb (``rope.take``) calls
            # ``passthrough()`` to invoke the same-named verb on the
            # parent class (``Zork Thing``'s substrate ``take``).
            #
            # Excluded: M-clause splits (turnfunc/preturnfunc/etc.).  An
            # M-END handler's RFALSE means "don't break the per-turn
            # chain"; running passthrough there would re-invoke the
            # substrate verb a second time.
            if self.action_owner and self._verbs_handled and not self._in_m_clause:
                return [f"{ind}return passthrough()"]
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
        if head == "PRINTD":
            # B.2: <PRINTD obj> prints the object's DESC.
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}print({obj}.desc(), end='')"]

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
            return [f"{ind}{obj}.moveto({dest})"]
        if head in ("REMOVE", "REMOVE-CAREFULLY"):
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}_.remove({obj})"]
        if head == "GOTO":
            room = self._translate_expr(form[1]) if len(form) > 1 else "None"
            return [f"{ind}_.goto({room})"]
        if head == "DO-WALK":
            direction = self._translate_expr(form[1]) if len(form) > 1 else '"north"'
            return [f"{ind}_.walk({direction})"]

        # --- flags ---
        if head == "FSET":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            flag = self._translate_flag_name(form[2]) if len(form) > 2 else '"unknown"'
            return [f"{ind}{obj}.set_flag({flag}, True)"]
        if head == "FCLEAR":
            obj = self._translate_expr(form[1]) if len(form) > 1 else "None"
            flag = self._translate_flag_name(form[2]) if len(form) > 2 else '"unknown"'
            return [f"{ind}{obj}.set_flag({flag}, False)"]

        # --- properties ---
        if head == "PUTP":
            obj = _as_object(self._translate_expr(form[1])) if len(form) > 1 else "None"
            prop = self._translate_prop_name(form[2]) if len(form) > 2 else '"unknown"'
            val = self._translate_expr(form[3]) if len(form) > 3 else "None"
            return [f"{ind}{obj}.set_property({prop}, {val})"]

        # --- global state ---
        if head == "SETG":
            key = str(form[1]).upper() if len(form) > 1 else "UNKNOWN"
            # F.2: parser-state slots are owned by DjangoMOO's parser; ZIL
            # routines that ``SETG`` them to set up a follow-up PERFORM
            # become no-ops since perform() takes its own args.
            if key in {"PRSA", "PRSO", "PRSI", "P-PRSA", "P-PRSO", "P-PRSI", "P-LEXV"}:
                return [f"{ind}pass  # SETG of parser-state slot is a no-op in DjangoMOO"]
            val = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}context.player.zstate_set({repr(key)}, {val})"]

        # --- score ---
        if head == "SCORE":
            delta = self._translate_expr(form[1]) if len(form) > 1 else "0"
            return [f"{ind}_.score_update({delta})"]

        # --- death ---
        if head == "JIGS-UP":
            msg = self._translate_expr(form[1]) if len(form) > 1 else '""'
            return [f"{ind}_.jigs_up({msg})"]

        # B.1: Z-machine session-control opcodes.  DjangoMOO doesn't have
        # ROM-snapshot save/restore or a process-level restart — the verbs
        # that wrap these (V-QUIT / V-RESTART / V-SAVE / V-RESTORE) emit
        # appropriate user messages and return False so the caller's COND
        # falls into its "Failed." branch.  Players quit via the standard
        # shell ``quit`` command, not these ZIL opcodes.
        if head == "QUIT":
            return [f"{ind}print('Goodbye.')", f"{ind}return"]
        if head == "RESTART":
            return [f"{ind}print('Restart not supported in DjangoMOO.')"]
        if head in ("RESTORE", "SAVE"):
            return [f"{ind}False  # {head}: Z-machine save/restore not supported"]

        # --- queue/interrupts ---
        if head == "ENABLE":
            inner = form[1] if len(form) > 1 else None
            if isinstance(inner, list) and inner:
                inner_head = str(inner[0]).upper()
                if inner_head == "QUEUE":
                    routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                    delay = self._translate_expr(inner[2]) if len(inner) > 2 else "1"
                    return [f"{ind}_.queue({routine}, {delay})"]
                if inner_head == "INT":
                    routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                    return [f"{ind}_.queue({routine}, 0)"]
            return [f"{ind}# ZIL: {form!r}  (ENABLE not translated)"]
        if head == "DISABLE":
            inner = form[1] if len(form) > 1 else None
            if isinstance(inner, list):
                routine = repr(str(inner[1]).lower().replace("_", "-")) if len(inner) > 1 else '"unknown"'
                return [f"{ind}_.cancel({routine})"]
            return [f"{ind}# ZIL: {form!r}  (DISABLE not translated)"]

        # --- perform (indirect verb call) ---
        if head == "PERFORM":
            verb_atom = self._translate_expr(form[1]) if len(form) > 1 else '"unknown"'
            prso = self._translate_expr(form[2]) if len(form) > 2 else "None"
            prsi = self._translate_expr(form[3]) if len(form) > 3 else "None"
            return [f"{ind}_.perform({verb_atom}, {prso}, {prsi})"]

        # --- local set ---
        if head == "SET":
            var = _sanitize_ident(str(form[1])) if len(form) > 1 else "v_unknown"
            val = self._translate_expr(form[2]) if len(form) > 2 else "None"
            return [f"{ind}{var} = {val}"]

        # DUMB-CONTAINER is a ZIL global utility that handles open/close/examine
        # for simple containers/pedestals, returning False for everything else.
        # Inline its logic so verbs it doesn't handle (e.g. "put") fall through
        # to run_v_routine rather than returning None from invoke_verb.
        if head == "DUMB-CONTAINER":
            return [
                f'{ind}if verb_name in ["open", "close", "shut", "look-inside"]:',
                f'{ind}    print("You can\'t do that.")',
                f"{ind}    return",
                f'{ind}elif verb_name in ["examine", "x", "describe", "what"]:',
                f'{ind}    print("It looks pretty much like a " + context.parser.get_dobj().desc() + ".")',
                f"{ind}    return",
            ]

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
            if upper == "PRSA" and self._in_m_clause:
                # In an M-clause, the do_command path injects the actual
                # player verb word as args[1] (the invoked verb's
                # ``player_verb`` is the verb name itself, "preturnfunc",
                # because parser.verb hasn't been resolved yet).  See
                # translate_m_clause for the binding line.
                return "the_player_verb"
            if upper in _GLOBAL_MAP:
                return _GLOBAL_MAP[upper]
            if upper in M_CLAUSES:
                # M-* event constants used in <EQUAL? .RARG ,M-LOOK>
                return repr(upper)
            if upper in self.object_atoms:
                # Bootstrap adds atom-form (lower-snake) as an alias on
                # every room/object so ``lookup()`` resolves rooms by their
                # ZIL atom regardless of the object's DESC (e.g.
                # SOUTH-TEMPLE → "Altar" — the atom alias matches).
                alias = atom.lower().replace("-", "_")
                return f"lookup({alias!r})"
            if upper in self.routine_atoms:
                # E + D-mild: predicates and snake-cased helpers reach
                # dot-syntax via ``_routine_dot_name``; only names that
                # still aren't valid identifiers fall back to invoke_verb.
                dot = _routine_dot_name(upper)
                if dot is not None:
                    return f"_.zork_thing.{dot}()"
                return f"_.zork_thing.invoke_verb({atom.lower()!r})"
            # Default: global state variable read.
            return f"context.player.zstate_get({repr(upper)})"

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

        # --- bit-test ---
        # ZIL ``<BTST a b>`` returns true if any bit set in ``b`` is also
        # set in ``a``.  Maps to Python ``(a & b) != 0`` — but since our
        # zstate values aren't always integers (some are None for
        # unpopulated parser globals), guard with ``or 0``.
        if head_upper == "BTST" and len(node) >= 3:
            a = self._translate_expr(node[1])
            b = self._translate_expr(node[2])
            return f"((({a}) or 0) & (({b}) or 0)) != 0"
        if head_upper == "BOR" and len(node) >= 3:
            args_expr = " | ".join(f"(({self._translate_expr(a)}) or 0)" for a in node[1:])
            return f"({args_expr})"
        if head_upper == "BAND" and len(node) >= 3:
            args_expr = " & ".join(f"(({self._translate_expr(a)}) or 0)" for a in node[1:])
            return f"({args_expr})"

        # --- COND in expression position ---
        # ``<COND (test1 expr1) (test2 expr2) (ELSE expr3)>`` translates
        # to a chained ternary.  Statement-context COND is handled by
        # ``_translate_cond``; without this branch, expression-context
        # COND falls through to the default head-as-function-call path
        # and emits an undefined ``cond(...)`` call.
        if head_upper == "COND":
            clauses = list(node[1:])
            # Build the ternary right-to-left so the first clause is the
            # outermost.  For each clause (test, ...body), use the last
            # body form as the value (or the test itself if no body).
            expr = "None"
            for clause in reversed(clauses):
                if not isinstance(clause, (list, tuple)) or not clause:
                    continue
                test = clause[0]
                body = list(clause[1:])
                test_is_else = isinstance(test, str) and test.upper() in ("ELSE", "T", "TRUE")
                value_expr = self._translate_expr(body[-1]) if body else self._translate_expr(test)
                if test_is_else:
                    expr = value_expr
                else:
                    test_expr = self._translate_expr(test)
                    expr = f"({value_expr} if {test_expr} else {expr})"
            return expr

        # --- APPLY: ZIL's "call this routine reference" ---
        # Common pattern: <APPLY <GETP obj ,P?ACTION> ,M-X>.  The action
        # routine's M-* clauses are already split into separate verbs on the
        # object (look/preturnfunc/turnfunc/enterfunc/exitfunc), so map the
        # apply directly to the corresponding ``invoke_verb``.  Other APPLY
        # forms fall through to the default head-as-name translation, which
        # is currently undefined-at-runtime (translator gap, see
        # ARCHITECTURE.md).
        if head_upper == "APPLY" and len(node) >= 3:
            target = node[1]
            arg = node[2]
            verb_name = None
            if isinstance(arg, str):
                arg_atom = arg.lstrip(",.").upper()
                verb_name = _M_TO_VERB.get(arg_atom)
            if verb_name and isinstance(target, list) and len(target) >= 3:
                t_head = target[0]
                if isinstance(t_head, str) and t_head.upper() in ("GETP", "GETPT"):
                    obj_expr = self._translate_expr(target[1])
                    # ``X.invoke_verb("foo")`` is safe only when X owns the
                    # verb directly.  ``recurse=False`` keeps us from
                    # falling through to a substrate inherited from
                    # ``$zork_thing`` — e.g. for ``M-LOOK`` on a vehicle
                    # without its own M-LOOK clause, the inherited
                    # ``look`` is V-LOOK which calls describe-room and
                    # recurses infinitely.
                    return (
                        f"({obj_expr}.invoke_verb({verb_name!r}) "
                        f"if {obj_expr} is not None and {obj_expr}.has_verb({verb_name!r}, recurse=False) "
                        f"else None)"
                    )

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
            # Direction-token check: <EQUAL? ,PRSO ,P?EAST ,P?WEST ...>
            # ZIL stores direction codes in PRSO; in DjangoMOO the dobj is
            # a string.  When LHS is PRSO and ALL operands are direction
            # atoms, emit a string comparison against get_dobj_str().
            if self._is_prso_atom(node[1]):
                dirs = [self._direction_string(a) for a in node[2:]]
                if all(d is not None for d in dirs):
                    if len(dirs) == 1:
                        return f"context.parser.get_dobj_str() == {dirs[0]!r}"
                    rhs = ", ".join(repr(d) for d in dirs)
                    return f"context.parser.get_dobj_str() in ({rhs})"
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
            return f"{obj}.flag({flag})"

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
            return f"_.next_sibling({obj})"
        if head_upper == "GLOBAL-IN?":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            loc = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"{obj}.global_in({loc})"

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
            return f"_.table_put({table}, {idx}, {val})"
        if head_upper == "READ":
            # F.2: <READ ,P-INBUF ,P-LEXV> is the Z-machine "read a line of
            # input" operation.  DjangoMOO has already parsed the player's
            # command by the time the verb body runs, so this is a no-op
            # — parser.words is already populated.
            return "None  # READ no-op (parser already populated)"
        if head_upper in ("GET", "GETB"):
            # F.2: <GET ,P-LEXV N> reads the Nth typed word from the
            # Z-machine parser buffer.  DjangoMOO exposes that as
            # parser.words[N-1] (1-indexed in ZIL).  GETB on P-LEXV with
            # ,P-LEXWORDS yields the word count.  Map both forms here so
            # the substrate routines (loud_room, finish, v_say/v_echo if
            # ever resurrected) read the live parser state.
            tbl_node = node[1] if len(node) > 1 else None
            idx_node = node[2] if len(node) > 2 else None
            if isinstance(tbl_node, str) and tbl_node.lstrip(",.").upper() == "P-LEXV":
                if isinstance(idx_node, str) and idx_node.lstrip(",.").upper() == "P-LEXWORDS":
                    return "len(context.parser.words)"
                idx_expr = self._translate_expr(idx_node) if idx_node is not None else "1"
                return f'(context.parser.words[({idx_expr}) - 1] if len(context.parser.words) >= ({idx_expr}) else "")'
            table = self._translate_expr(tbl_node) if tbl_node is not None else "None"
            idx = self._translate_expr(idx_node) if idx_node is not None else "0"
            return f"_.table_get({table}, {idx})"

        # --- properties ---
        if head_upper == "GETP":
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            prop = self._translate_prop_name(node[2]) if len(node) > 2 else '"unknown"'
            # ZIL ``<GETP obj prop>`` returns 0 for missing properties; use the
            # SDK helper so verb code never raises NoSuchPropertyError.
            return f"{obj}.getp({prop})"
        if head_upper == "PUTP":
            obj = _as_object(self._translate_expr(node[1])) if len(node) > 1 else "None"
            prop = self._translate_prop_name(node[2]) if len(node) > 2 else '"unknown"'
            val = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"{obj}.set_property({prop}, {val})"

        # --- global state read ---
        if head_upper == "SETG":
            key = str(node[1]).upper() if len(node) > 1 else "UNKNOWN"
            # F.2: PRSA/PRSO/PRSI/P-PRSO/P-PRSI/P-LEXV are Z-machine parser-
            # state slots that DjangoMOO populates from its own parser.  ZIL
            # routines that ``SETG`` them to set up a follow-up PERFORM are
            # better expressed by passing args to perform() directly; mute
            # the SETG so the no-longer-meaningful slot writes don't show up
            # as primitive leakage.
            if key in {"PRSA", "PRSO", "PRSI", "P-PRSA", "P-PRSO", "P-PRSI", "P-LEXV"}:
                return "None  # SETG of parser-state slot is a no-op in DjangoMOO"
            val = self._translate_expr(node[2]) if len(node) > 2 else "None"
            return f"context.player.zstate_set({repr(key)}, {val})"
        if head_upper == "GVAL":
            key = str(node[1]).upper() if len(node) > 1 else "UNKNOWN"
            if key in _GLOBAL_MAP:
                return _GLOBAL_MAP[key]
            return f"context.player.zstate_get({repr(key)})"

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
        if head_upper == "PRINTD":
            # B.2: <PRINTD obj> prints the object's DESC.
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f"print({obj}.desc(), end='')"
        if head_upper == "PICK-ONE":
            table = self._translate_expr(node[1]) if len(node) > 1 else '"unknown"'
            return f"_.pick({table})"

        # --- verb dispatch ---
        if head_upper == "VERB?":
            verbs = [str(v).upper() for v in node[1:] if isinstance(v, str)]
            aliases: list[str] = []
            for v in verbs:
                aliases.extend(ZIL_VERBS.get(v, [v.lower()]))
            self._verbs_handled.update(aliases)
            # ``the_player_verb`` is the actual player-typed verb (ZIL PRSA).
            # We can't use ``verb_name`` here because:
            #   * Inside an M-clause the M-* dispatcher's verb_name is
            #     ``preturnfunc``/``turnfunc``, not the player verb.
            #   * When a routine is invoked from another routine
            #     (e.g. trap-door's open.py calling open_close), the
            #     callee's verb_name is its own name (``open_close``),
            #     not the player verb.
            # In M-clauses, do_command supplies the player verb via
            # ``args[1]`` and we bind ``the_player_verb`` in the unpack.
            # In non-M-clause routines, we derive it from ``context.parser``
            # at the top of the body (see ``translate()``).
            var = "the_player_verb"
            # Single-element membership reads better as direct equality.
            if len(aliases) == 1:
                return f"{var} == {aliases[0]!r}"
            return f"{var} in {aliases!r}"

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
            return f"_.score_update({delta})"

        # --- death ---
        if head_upper == "JIGS-UP":
            msg = self._translate_expr(node[1]) if len(node) > 1 else '""'
            return f"_.jigs_up({msg})"

        # B.1: Z-machine session-control opcodes when used in expression
        # position (e.g. ``<COND (<RESTORE> ...)>``).  Emit values that
        # the surrounding COND will treat appropriately — ``QUIT`` becomes
        # an unreachable expression (the statement form prints+returns),
        # save/restore/restart all yield falsy so the "Failed." branch fires.
        if head_upper == "QUIT":
            return "None  # QUIT in expression position"
        if head_upper == "RESTART":
            return "False  # RESTART not supported"
        if head_upper in ("RESTORE", "SAVE"):
            return f"False  # {head_upper}: not supported"

        # --- desc ---
        if head_upper in ("OBJECT-PNAME",):
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f"{obj}.desc()"

        # --- predicates ---
        if head_upper == "OPENABLE?":
            obj = self._translate_expr(node[1]) if len(node) > 1 else "None"
            return f'{obj}.flag("openable")'

        # --- perform ---
        if head_upper == "PERFORM":
            verb_atom = self._translate_expr(node[1]) if len(node) > 1 else '"unknown"'
            prso = self._translate_expr(node[2]) if len(node) > 2 else "None"
            prsi = self._translate_expr(node[3]) if len(node) > 3 else "None"
            return f"_.perform({verb_atom}, {prso}, {prsi})"

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
            # Known routine call (e.g. ``<ITAKE>`` from ``<EQUAL? <ITAKE> T>``,
            # or ``<FOREST-ROOM?>`` predicate, or ``<THIS-IS-IT obj>``).  E +
            # D-mild: dot-syntax via ``_routine_dot_name`` covers predicates
            # and snake-cased helpers; only names that still aren't valid
            # identifiers fall back to ``invoke_verb``.
            if atom in self.routine_atoms or atom.endswith("?"):
                dot = _routine_dot_name(atom)
                if dot is not None:
                    return f"_.zork_thing.{dot}()"
                return f"_.zork_thing.invoke_verb({atom.lower()!r})"
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
                # E + D-mild: dot-syntax via ``_routine_dot_name`` covers
                # predicates (``is_<base>``) and snake-cased helpers
                # (``this_is_it``).  Names that don't sanitise to valid
                # identifiers (``v?something``, etc.) fall back to
                # ``invoke_verb``.
                dot = _routine_dot_name(head_upper)
                if dot is not None:
                    return f"_.zork_thing.{dot}({args_expr})"
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
                    segments.append(f"{obj}.desc()")
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

        # A.5: a COND whose only clause is ``(T body)`` / ``(ELSE body)`` is
        # equivalent to the bare body — no need for an ``if True:`` wrapper.
        # Detect and inline before walking clauses.
        meaningful = [c for c in clauses if isinstance(c, (list, tuple)) and c]
        if len(meaningful) == 1 and isinstance(meaningful[0][0], str) and meaningful[0][0].upper() in ("T", "ELSE"):
            body = list(meaningful[0][1:])
            return self._translate_body(body, indent) if body else []

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

    # Captures `lookup("name")` or `lookup('name')` calls; group(2) is the atom.
    _LOOKUP_RE = re.compile(r"\blookup\((['\"])([^'\"]+)\1\)")

    def _fix_return_print(self, lines: list[str]) -> list[str]:
        """Split ``return print(...)`` into ``print(...)`` followed by ``return``.

        ``print()`` returns ``None``, so the wrapping ``return`` only carried
        the routine's exit semantics — never a useful value.  Splitting into
        two lines makes the intent explicit (print, then return) and avoids
        the misleading look of ``return print(...)``.  An explicit ``return``
        is still emitted so the routine exits at this point rather than
        falling through to subsequent code."""
        out = []
        for line in lines:
            stripped = line.lstrip(" ")
            indent_chars = line[: len(line) - len(stripped)]
            if stripped.startswith("return print("):
                out.append(indent_chars + stripped[len("return ") :])
                out.append(indent_chars + "return")
            else:
                out.append(line)
        return out

    def _replace_self_lookup_with_this(self, lines: list[str]) -> list[str]:
        """When the verb is owned by an object atom, rewrite ``lookup("atom")``
        → ``this`` in body lines.  The translator can't always know which
        atom the verb belongs to up front (M-* clauses, shared ACTIONs, …),
        but at emission time ``self.action_owner`` settles it."""
        if not self.action_owner:
            return lines
        owner_atom, _is_room = self.action_owner
        target = owner_atom.lower().replace("-", "_")
        # Match the atom either as-is or with hyphens-to-underscores.
        targets = {owner_atom.lower(), target}

        def repl(m: re.Match) -> str:
            return "this" if m.group(2).lower() in targets else m.group(0)

        return [self._LOOKUP_RE.sub(repl, line) for line in lines]

    def _cache_repeated_lookups(self, lines: list[str]) -> tuple[list[str], list[str]]:
        """Hoist ``lookup("X")`` calls used 2+ times into a local variable.

        Returns ``(hoist_lines, rewritten_lines)``.  Hoist lines are emitted
        at the top of the body so the variable is in scope for every
        reference."""
        counts: dict[str, int] = {}
        for line in lines:
            for m in self._LOOKUP_RE.finditer(line):
                counts[m.group(2)] = counts.get(m.group(2), 0) + 1

        hoisted: dict[str, str] = {}
        for atom, count in sorted(counts.items()):
            if count < 2:
                continue
            ident = re.sub(r"[^a-z0-9_]", "_", atom.lower())
            if not ident or ident[0].isdigit():
                continue
            # Avoid colliding with python keywords or builtins.
            if ident in _PY_KEYWORDS or ident in _PY_BUILTIN_SHADOWS:
                ident = ident + "_o"
            hoisted[atom] = ident

        if not hoisted:
            return [], lines

        def repl(m: re.Match) -> str:
            atom = m.group(2)
            return hoisted.get(atom, m.group(0))

        rewritten = [self._LOOKUP_RE.sub(repl, line) for line in lines]
        hoist_lines = [f'{var} = lookup("{atom}")' for atom, var in hoisted.items()]
        return hoist_lines, rewritten

    def _maybe_hoist_parser(self, lines: list[str]) -> tuple[list[str], list[str]]:
        """If body uses ``context.parser.X`` at all, emit
        ``parser = context.parser`` once at the top and rewrite subsequent
        references to ``parser.X``.  Even single-use sites read better with
        the alias."""
        if not any("context.parser." in line for line in lines):
            return [], lines
        rewritten = [line.replace("context.parser.", "parser.") for line in lines]
        return ["parser = context.parser"], rewritten

    def _maybe_hoist_player(self, lines: list[str]) -> tuple[list[str], list[str]]:
        """If body uses ``context.player`` at all, emit ``player =
        context.player`` once at the top and rewrite all references — both
        ``context.player.X`` and bare ``context.player``.  Even single-use
        sites read better with the alias."""
        if not any("context.player" in line for line in lines):
            return [], lines
        rewritten = [line.replace("context.player", "player") for line in lines]
        return ["player = context.player"], rewritten

    def _polish(self, body_lines: list[str], unpack_lines: list[str]) -> tuple[list[str], list[str]]:
        """Apply readability transforms to translated body + unpack lines.

        Order matters: fix-return-print and self-lookup-to-this are pure
        line rewrites; lookup caching scans both unpack and body to find
        repeated atoms; parser hoist runs last so it sees the final body."""
        body_lines = self._fix_return_print(body_lines)
        body_lines = self._replace_self_lookup_with_this(body_lines)

        cache_lines, combined = self._cache_repeated_lookups(unpack_lines + body_lines)
        unpack_lines = combined[: len(unpack_lines)]
        body_lines = combined[len(unpack_lines) :]

        parser_hoist, combined = self._maybe_hoist_parser(unpack_lines + body_lines)
        unpack_lines = combined[: len(unpack_lines)]
        body_lines = combined[len(unpack_lines) :]

        player_hoist, combined = self._maybe_hoist_player(unpack_lines + body_lines)
        unpack_lines = combined[: len(unpack_lines)]
        body_lines = combined[len(unpack_lines) :]

        # Hoists + cache lines go at the top of unpack_lines so they're
        # available to the body (and to any unpack default expressions).
        prelude = player_hoist + parser_hoist + cache_lines
        if prelude:
            unpack_lines = prelude + unpack_lines
        return body_lines, unpack_lines

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
        """Translate a ZIL flag atom to the DjangoMOO property name string.

        When the flag is given as a local-variable deref (``.AV`` where
        ``AV`` is a routine param/aux), emit the variable expression so
        ``<FSET? .RM .AV>`` translates to ``flag(rm, av)`` — letting the
        runtime use whatever atom is currently bound to ``av``.
        """
        if isinstance(node, list) and node:
            # ,FLAGNAME is parsed as a list [FLAGNAME] in some contexts
            node = node[0] if len(node) == 1 else node
        if isinstance(node, str):
            # Variable-deref ``.X`` — emit the local variable name when
            # X matches a routine param or aux var.
            if node.startswith("."):
                bare = node[1:]
                local_atoms = {p.upper() for p in self.routine.params + self.routine.aux_vars}
                if bare.upper() in local_atoms:
                    return _sanitize_ident(bare.upper())
            upper = node.lstrip(",.").upper()
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
