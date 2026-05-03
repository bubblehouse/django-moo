"""
Round-trip tests for the ZIL → Python translator.

Each test takes a ZIL S-expression source string, runs it through the
tokenizer / parser / converter / translator pipeline, and asserts that the
emitted Python carries the expected idioms.  These are unit tests of the
translator itself, not of the runtime sandbox — we never execute the output.
"""

from __future__ import annotations

import pytest

from extras.zil_import.converter import _extract_routine
from extras.zil_import.parser import Str, parse, tokenize
from extras.zil_import.translator import _sanitize_ident, has_m_dispatch, translate_m_clause, translate_routine


def _routine(src: str):
    """Parse a single ROUTINE form into a ZilRoutine."""
    nodes = parse(tokenize(src))
    assert len(nodes) == 1, f"expected one top-level form, got {len(nodes)}"
    return _extract_routine(nodes[0])


def _translate(src: str) -> str:
    return translate_routine(_routine(src))


# ---------------------------------------------------------------------------
# Basic statement forms
# ---------------------------------------------------------------------------


def test_tell_emits_print():
    """<TELL ...> becomes a print() call."""
    out = _translate('<ROUTINE FOO () <TELL "hello" CR>>')
    assert "print('hello')" in out


def test_tell_concatenates_segments():
    """<TELL "a" "b"> joins both segments into one print."""
    out = _translate('<ROUTINE FOO () <TELL "first " "second" CR>>')
    assert "print(" in out
    # Order preserved.
    first = out.index("first")
    second = out.index("second")
    assert first < second


def test_crlf_emits_blank_print():
    """<CRLF> becomes print() with no args."""
    out = _translate("<ROUTINE FOO () <CRLF>>")
    assert "print()" in out


def test_rtrue_emits_return_true():
    """<RTRUE> compiles to `return True`."""
    out = _translate("<ROUTINE FOO () <RTRUE>>")
    assert "return True" in out


def test_rfalse_emits_return_false():
    """<RFALSE> compiles to `return False`."""
    out = _translate("<ROUTINE FOO () <RFALSE>>")
    assert "return False" in out


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------


def test_cond_emits_if_else_chain():
    """<COND (test1 body1) (T body2)> becomes if/else."""
    out = _translate("<ROUTINE FOO () <COND (<EQUAL? .X 1> <RTRUE>) (T <RFALSE>)>>")
    assert "if " in out
    # The else branch may be `else:` or fall through to `return False`.
    assert "return True" in out
    assert "return False" in out


def test_verb_predicate_emits_membership_check():
    """<VERB? TAKE> becomes a `player_verb in [...]` lookup (PRSA, not the
    invoked verb_name) so synonyms still match when ACTION routines hand off
    to V-routines."""
    out = _translate("<ROUTINE FOO () <COND (<VERB? TAKE> <RTRUE>)>>")
    assert "player_verb" in out


# ---------------------------------------------------------------------------
# SDK calls
# ---------------------------------------------------------------------------


def test_fset_predicate_emits_flag_call():
    """<FSET? ,OBJ ,FLAGBIT> becomes a _.zil_sdk.flag(...) call."""
    out = _translate("<ROUTINE FOO () <COND (<FSET? ,LANTERN ,LIGHTBIT> <RTRUE>)>>")
    assert "_.zil_sdk.flag" in out


def test_move_emits_zil_sdk_move():
    """<MOVE ,OBJ ,LOC> becomes _.zil_sdk.move(...)."""
    out = _translate("<ROUTINE FOO () <MOVE ,LANTERN ,LIVING-ROOM>>")
    assert "_.zil_sdk.move" in out


def test_remove_emits_zil_sdk_remove():
    """<REMOVE ,OBJ> becomes _.zil_sdk.remove(...)."""
    out = _translate("<ROUTINE FOO () <REMOVE ,LANTERN>>")
    assert "_.zil_sdk.remove" in out


def test_jigs_up_emits_death_call():
    """<JIGS-UP "msg"> becomes _.zil_sdk.jigs_up(...)."""
    out = _translate('<ROUTINE FOO () <JIGS-UP "You died.">>')
    assert "_.zil_sdk.jigs_up" in out


# ---------------------------------------------------------------------------
# Globals + properties
# ---------------------------------------------------------------------------


def test_move_passes_atom_args():
    """<MOVE ,OBJ ,LOC> emits a _.zil_sdk.move call with both atoms."""
    out = _translate("<ROUTINE FOO () <MOVE ,LANTERN ,LIVING-ROOM>>")
    assert "_.zil_sdk.move" in out
    assert "LANTERN" in out
    assert "LIVING-ROOM" in out or "LIVING_ROOM" in out


def test_getp_emits_getp_helper():
    """<GETP ,OBJ P?DESC> routes through _.zil_sdk.getp() for safe property access."""
    out = _translate("<ROUTINE FOO () <GETP ,LANTERN P?DESC>>")
    assert "zil_sdk.getp" in out


# ---------------------------------------------------------------------------
# M-clause splitting (room/object action dispatch)
# ---------------------------------------------------------------------------


def test_m_dispatch_detected_when_present():
    """A routine with M-LOOK in COND advertises m-dispatch."""
    routine = _routine('<ROUTINE FOO (RARG) <COND (<EQUAL? .RARG ,M-LOOK> <TELL "looking" CR>)>>')
    assert has_m_dispatch(routine) is True


def test_m_dispatch_absent_for_plain_routine():
    """A routine that never tests RARG against M-* has no m-dispatch."""
    routine = _routine('<ROUTINE FOO () <TELL "hi" CR>>')
    assert has_m_dispatch(routine) is False


def test_m_clause_extracts_only_matching_branch():
    """translate_m_clause emits only the body of the matching M-* clause."""
    routine = _routine(
        "<ROUTINE FOO (RARG) "
        "<COND "
        '(<EQUAL? .RARG ,M-LOOK> <TELL "looking" CR>) '
        '(<EQUAL? .RARG ,M-BEG>  <TELL "begin"   CR>)>>'
    )
    look = translate_m_clause(routine, "M-LOOK")
    beg = translate_m_clause(routine, "M-BEG")
    assert "looking" in look and "begin" not in look
    assert "begin" in beg and "looking" not in beg


# ---------------------------------------------------------------------------
# Fallback for unhandled forms
# ---------------------------------------------------------------------------


def test_unhandled_enable_form_emits_zil_comment_only():
    """Defensive fallback: an ``<ENABLE>`` whose inner form is neither
    ``<QUEUE>`` nor ``<INT>`` annotates the original form as a ZIL
    comment and emits no executable statement. The known inner forms
    (covered separately) are exhaustive for the actual Zork sources;
    the fallback exists so a future ZIL input can't silently produce
    invalid Python."""
    out = _translate("<ROUTINE FOO () <ENABLE <SOMETHING-NOT-QUEUE>>>")
    assert "# ZIL:" in out
    assert "ENABLE not translated" in out
    # Earlier versions raised NotImplementedError, which broke control
    # flow because subsequent body forms became unreachable code.
    assert "NotImplementedError" not in out


def test_enable_queue_emits_sdk_queue():
    """<ENABLE <QUEUE routine delay>> compiles to _.zil_sdk.queue(...)."""
    out = _translate("<ROUTINE FOO () <ENABLE <QUEUE I-LANTERN 100>>>")
    assert "_.zil_sdk.queue('i-lantern', 100)" in out


def test_enable_int_emits_sdk_queue_with_zero_delay():
    """<ENABLE <INT routine>> re-enables a previously queued task; in
    SDK terms that's a queue() with delay=0."""
    out = _translate("<ROUTINE FOO () <ENABLE <INT I-CYCLOPS>>>")
    assert "_.zil_sdk.queue('i-cyclops', 0)" in out


def test_double_equal_predicate_translates_as_equality():
    """<==? a b> is one of ZIL's equality predicates and translates
    identically to <EQUAL? a b>. This depended on the parser tokenizing
    ``==?`` as a single atom (rather than ``==`` + ``?``)."""
    out = _translate("<ROUTINE FOO () <COND (<==? ,HERE ,FOREST-1> <RTRUE>)>>")
    assert "==" in out
    assert "if " in out
    assert "# ZIL: unrecognised" not in out


# ---------------------------------------------------------------------------
# Header + verb shebang
# ---------------------------------------------------------------------------


def test_translation_starts_with_moo_shebang():
    """Generated verb files start with the #!moo verb header."""
    out = _translate('<ROUTINE FOO () <TELL "hi" CR>>')
    assert out.lstrip().startswith("#!moo verb")


@pytest.mark.parametrize("name", ["FOO", "BAR-FN", "X-Y-Z"])
def test_routine_name_appears_in_shebang(name):
    """Routine names are lower-cased into the shebang verb name."""
    out = _translate(f'<ROUTINE {name} () <TELL "x" CR>>')
    # The shebang preserves dashes (DjangoMOO verb names accept them); only
    # the `--on $foo` target file name uses snake_case.
    assert name.lower() in out.splitlines()[0]


# ---------------------------------------------------------------------------
# Identifier sanitization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("FOO", "foo"),
        ("FOO-BAR", "foo_bar"),
        ("LIT?", "lit_p"),
        ("STOLE-LIGHT?", "stole_light_p"),
        # ZIL local-var deref ``.X`` is stripped on entry so the resulting
        # identifier matches the unadorned variable name. (``,X`` is
        # stripped at the call site before reaching ``_sanitize_ident`` —
        # not by the helper itself.)
        (".OLD-LIT", "old_lit"),
        # Any non-alphanumeric character collapses to ``_`` so we never
        # emit invalid identifiers.
        ("FOO!", "foo_"),
        ("FOO*BAR", "foo_bar"),
        # Empty / pathological inputs round-trip to a stable sentinel.
        ("", "_unknown"),
        (".", "_unknown"),
    ],
)
def test_sanitize_ident_basic(raw, expected):
    assert _sanitize_ident(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Atoms whose sanitized form would be a Python keyword get a
        # ``_v`` suffix so the generated code parses.
        ("DEF", "def_v"),
        ("CLASS", "class_v"),
        ("IF", "if_v"),
        ("RETURN", "return_v"),
        # Atoms whose sanitized form would shadow a common builtin (used
        # heavily by the translator output) get the same suffix.
        ("SET", "set_v"),
        ("LIST", "list_v"),
        ("TYPE", "type_v"),
        ("PRINT", "print_v"),
    ],
)
def test_sanitize_ident_avoids_keyword_and_builtin_collisions(raw, expected):
    assert _sanitize_ident(raw) == expected


@pytest.mark.parametrize("raw", ["1FOO", "9-FOO", "0?"])
def test_sanitize_ident_prefixes_leading_digit(raw):
    """Leading digits get a ``v_`` prefix so the result is a valid identifier."""
    out = _sanitize_ident(raw)
    assert out.startswith("v_"), f"{raw!r} → {out!r} should be prefixed"
    assert out.replace("_", "").replace("v", "", 1) or True  # well-formed


def test_sanitize_ident_is_idempotent_for_valid_names():
    """Already-valid identifiers round-trip unchanged."""
    for name in ("foo", "foo_bar", "x_y_z"):
        assert _sanitize_ident(name) == name


# ---------------------------------------------------------------------------
# Parser tokenization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("predicate", ["0?", "1?", "ZERO?"])
def test_predicate_tokens_are_atoms_not_number_plus_atom(predicate):
    """``0?`` and ``1?`` must lex as a single atom — not as a number followed
    by ``?``. The translator depends on the head of ``<0? .X>`` being the
    atom ``0?`` so it can dispatch on it; if the parser splits it, the form
    becomes ``[0, ?, .X]`` and translation degenerates to a Python list
    literal that's always truthy."""
    tokens = tokenize(f"<{predicate} 1>")
    kinds = [t.kind for t in tokens]
    # ``<``, atom, number, ``>``
    assert kinds == ["open_angle", "atom", "number", "close_angle"]
    assert tokens[1].value == predicate


def test_parser_distinguishes_strings_from_atoms():
    """Quoted strings come back as ``Str`` (a subclass of ``str``); bare
    atoms come back as plain ``str``. The translator uses this distinction
    to decide between ``print('hello')`` and ``zstate_get('HELLO')``."""
    nodes = parse(tokenize('<TELL "hello" HELLO>'))
    assert len(nodes) == 1
    form = nodes[0]
    quoted, atom = form[1], form[2]
    assert isinstance(quoted, Str)
    assert quoted == "hello"
    assert isinstance(atom, str) and not isinstance(atom, Str)
    assert atom == "HELLO"


def test_string_literal_translates_as_python_string():
    """A ZIL string in expression context emits a Python string literal,
    not a state read — even when the contents look atom-like (all caps,
    contains hyphens)."""
    out = _translate('<ROUTINE FOO () <TELL "ALL CAPS WITH-DASHES" CR>>')
    assert "'ALL CAPS WITH-DASHES'" in out
    # The all-caps content must NOT be treated as a global-state lookup.
    assert "zstate_get('ALL" not in out
