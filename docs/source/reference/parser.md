# Command Parser Reference

This page is the reference for the command parser: lexer attributes,
parser methods verbs use to read parsed arguments, the preposition
synonym table, and the verb search order. For the conceptual overview
(grammar, BNF, lexer behaviour, the `$do_command` hook), see
{doc}`../explanation/parser`.

## Lexer

The lexer turns a raw command string into a structured `Lexer`
instance. It is internal plumbing; verb code never constructs one
directly. It's described here for completeness — verbs interact with
the `Parser` instance attached to `context.parser`.

```{eval-rst}
.. py:currentmodule:: moo.core.parse
.. autoattribute:: Lexer.command
.. autoattribute:: Lexer.words
.. autoattribute:: Lexer.dobj_str
.. autoattribute:: Lexer.dobj_spec_str
.. autoattribute:: Lexer.prepositions
```

## Parser

`Parser` consumes a `Lexer` plus the caller object and resolves names
to Objects.

```{eval-rst}
.. py:currentmodule:: moo.core.parse
.. autoattribute:: Parser.caller
.. autoattribute:: Parser.command
.. autoattribute:: Parser.words
.. autoattribute:: Parser.dobj_str
.. autoattribute:: Parser.dobj_spec_str
.. autoattribute:: Parser.dobj
.. autoattribute:: Parser.prepositions
.. autoattribute:: Parser.verb
.. autoattribute:: Parser.this
```

Most of these are read internally during dispatch. The two things
verb code actually uses on `context.parser` are `context.parser.command`
(the original command string) and the argument-extraction methods,
listed next.

## Parser methods

```{eval-rst}
.. py:currentmodule:: moo.core.parse
.. automethod:: Parser.get_dobj
.. automethod:: Parser.get_dobj_str
.. automethod:: Parser.has_dobj
.. automethod:: Parser.has_dobj_str
.. automethod:: Parser.get_pobj
.. automethod:: Parser.get_pobj_str
.. automethod:: Parser.get_pobj_spec_str
.. automethod:: Parser.has_pobj
.. automethod:: Parser.has_pobj_str
```

Use `get_*_str()` when the argument is plain text (a message, a name
to create, etc.). Use `get_*()` when you expect the argument to refer
to an existing game object — and let the exception propagate if it
doesn't. The task runner shows a clean error to the player; you don't
need a `try/except` just to report the failure. See
{doc}`../how-to/creating-verbs` for the canonical patterns.

## Object resolution

When the parser encounters a name in the command, it resolves it to
an Object using these rules in order:

| Form | Resolution |
|------|------------|
| `me` | The caller (the player who typed the command). |
| `here` | The caller's location. |
| `#N` (e.g. `#22`) | The Object with that primary key. Raises `NoSuchObjectError` if no such Object exists. |
| `my <name>` | Search the caller's inventory for `<name>`. |
| `<player>'s <name>` | Find `<player>` in the caller's location, then search their inventory for `<name>`. Raises `NoSuchObjectError` for the player if they're not in the room. |
| `<name>` (no specifier) | Search the caller's location first; if no match, fall back to the caller's inventory. |

All name and alias matches are case-insensitive. Hidden-placement
objects (placed `under` or `behind` something) are excluded from
location searches by name. They can only be reached by `look under
<target>` or `look behind <target>`, which read the placement table
directly.

`get_dobj(lookup=True)` and `get_pobj(prep, lookup=True)` add a final
fallback to a global `lookup()` if no local match exists. Local
matches always win — `@obvious crate` matches the crate in your room
even when a "wooden crate" exists elsewhere in the world.

## Preposition synonym groups

`settings.PREPOSITIONS` defines preposition synonym groups. Words in
the same group are interchangeable; the parser normalises every
synonym to the first (canonical) word in the group when storing the
parsed result.

| Canonical | Synonyms |
|-----------|----------|
| `with` | `using` |
| `at` | `to` |
| `before` | `in front of` |
| `in` | `inside`, `into`, `within` |
| `on` | `onto`, `upon`, `above`, `on top of` |
| `from` | `out of`, `from inside` |
| `over` | |
| `through` | |
| `under` | `underneath`, `beneath`, `below` |
| `around` | `round` |
| `between` | `among` |
| `behind` | `past` |
| `beside` | `by`, `near`, `next to`, `along` |
| `for` | `about` |
| `is` | |
| `as` | |
| `off` | `off of` |

Verb authors should use the canonical (first) form in `--ispec`
shebang options and in parser API calls such as
`get_pobj_str("with")`. Synonyms also work transparently if passed
directly to those methods, but staying canonical avoids surprises.

## Verb search

After resolving objects, the parser searches for a matching verb in
this order:

1. The caller.
2. Objects in the caller's inventory.
3. The caller's location.
4. The direct object, if any.
5. The objects of any prepositions, if any.

For each candidate, dispatch checks:

1. The caller has `read` permission on the object.
2. The object (or one of its ancestors) defines a verb whose name and
   argument specifiers match the command.

Verb name matching supports a single `*` for prefix matching
(`foo*bar`, `foo*`, `*`). See {doc}`verbs` for the grammar.

### Last match wins

The search iterates through every candidate and **overwrites**
`parser.this` on each match. The final match in the search order is
the one that executes. This is the "last match wins" rule.

When both the caller and the direct object are `$player` instances
(or both inherit the same verb from a common ancestor), the direct
object wins because it appears later in the search order. Inside the
executing verb:

```
@gag Player   →   this = Player (dobj), context.player = Wizard (caller)
page Player   →   this = Player (dobj), context.player = Wizard (caller)
```

**Use `context.player` to identify who initiated a command.** Only
use `this` when the verb is specifically designed to act on the
object it was dispatched on (a room's `accept` verb, an exit's `go`
verb, etc.). The LambdaMOO permission idiom
`if player != this: return "Permission denied."` is broken in
DjangoMOO for any verb with a dspec — it fires on every normal
invocation.
