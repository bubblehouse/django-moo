"""
ZIL S-expression tokenizer and parser.

ZIL (Zork Implementation Language) is an MDL/Lisp dialect. This parser handles:
  - <FORM arg1 arg2 ...>   angle-bracket forms (primary construct)
  - (elem1 elem2 ...)      parenthesized property lists (inside ROOM/OBJECT defs)
  - "string"               double-quoted strings (| = newline, \" = literal quote)
  - ; comment              line comments
  - atoms                  identifiers (may contain letters, digits, -, ?, !)
  - integers               decimal numbers, optionally signed
  - <>                     nil/false
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Union

# A parsed node is one of these types
Atom = str  # upper-case identifier or keyword
Number = int
Nil = type(None)  # <>
Form = list  # [head, arg1, arg2, ...] — angle-bracket form
Group = tuple  # (elem, ...) — parenthesized property group
Str = str  # string literal (stored as plain str, indistinguishable from Atom at type level)

Node = Union[str, int, None, list, tuple]


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r'(?P<string>"(?:[^"\\]|\\.|[^"])*")'
    r"|"
    r"(?P<nil><>)"
    r"|"
    r"(?P<open_angle><)"
    r"|"
    r"(?P<close_angle>>)"
    r"|"
    r"(?P<open_paren>\()"
    r"|"
    r"(?P<close_paren>\))"
    r"|"
    r"(?P<semicolon>;)"
    r"|"
    r"(?P<number>-?\d+)"
    r"|"
    r"(?P<atom>[A-Za-z0-9_.?!*#+\-][A-Za-z0-9_.?!*#+\-]*)"
    r"|"
    r"(?P<ws>\s+)",
    re.DOTALL,
)


@dataclass
class Token:
    kind: str
    value: str
    line: int
    offset: int = 0  # byte offset into source, for raw_zil capture


def tokenize(source: str) -> list[Token]:
    tokens = []
    line = 1
    for m in _TOKEN_RE.finditer(source):
        kind = m.lastgroup
        value = m.group()
        if kind == "ws":
            line += value.count("\n")
            continue
        tokens.append(Token(kind=kind, value=value, line=line, offset=m.start()))
        line += value.count("\n")
    return tokens


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class ParseError(Exception):
    pass


def _parse_string(raw: str) -> str:
    """Decode a ZIL string token (strip quotes, handle | newlines and \\ escapes)."""
    inner = raw[1:-1]
    result = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\":
            i += 1
            result.append(inner[i] if i < len(inner) else "\\")
        elif ch == "|":
            result.append("\n")
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def parse(tokens: list[Token]) -> list[Node]:
    """Parse a flat token list into a list of top-level nodes."""
    pos = 0

    def peek() -> Token | None:
        return tokens[pos] if pos < len(tokens) else None

    def consume() -> Token:
        nonlocal pos
        tok = tokens[pos]
        pos += 1
        return tok

    def parse_one() -> Node:
        tok = peek()
        if tok is None:
            raise ParseError("Unexpected end of input")

        if tok.kind == "nil":
            consume()
            return None

        if tok.kind == "number":
            consume()
            return int(tok.value)

        if tok.kind == "string":
            consume()
            return _parse_string(tok.value)

        if tok.kind == "atom":
            consume()
            return tok.value.upper()

        if tok.kind == "open_angle":
            consume()
            items = []
            while True:
                t = peek()
                if t is None:
                    raise ParseError("Unterminated <...> form")
                if t.kind == "close_angle":
                    consume()
                    break
                val = parse_one()
                if val is not None:  # filter expression-comment sentinels
                    items.append(val)
            return items  # Form

        if tok.kind == "open_paren":
            consume()
            items = []
            while True:
                t = peek()
                if t is None:
                    raise ParseError("Unterminated (...) group")
                if t.kind == "close_paren":
                    consume()
                    break
                val = parse_one()
                if val is not None:  # filter expression-comment sentinels
                    items.append(val)
            return tuple(items)  # Group

        if tok.kind == "semicolon":
            # ZIL expression comment: `;EXPR` — consume and discard the next expression.
            # If the next token is a closer or EOF, just skip the semicolon itself.
            consume()
            nxt = peek()
            if nxt is not None and nxt.kind not in ("close_angle", "close_paren"):
                try:
                    parse_one()  # discard
                except ParseError:
                    pass
            return None  # sentinel — filtered out by callers

        if tok.kind == "close_angle":
            raise ParseError(f"Unexpected '>' at line {tok.line}")
        if tok.kind == "close_paren":
            raise ParseError(f"Unexpected ')' at line {tok.line}")

        raise ParseError(f"Unknown token {tok!r}")

    results = []
    while pos < len(tokens):
        results.append(parse_one())
    return results


def parse_file(path: str) -> tuple[list[Node], str]:
    """Parse a ZIL source file. Returns (nodes, source_text)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        source = f.read()
    tokens = tokenize(source)
    return parse(tokens), source
