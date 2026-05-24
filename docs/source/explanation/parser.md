# How Command Parsing Works

The DjangoMOO server has a fairly robust parser for handling the
commands a player types. It can interpret any imperative command of
the forms:

    verb
    verb direct-object
    verb (the|my|player's) direct-object
    verb direct-object preposition object-of-the-preposition
    verb preposition object-of-the-preposition

and combinations thereof. The pseudo-BNF:

    <verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

Concrete examples:

    look
    take phil's book
    take the yellow bird
    put yellow bird in my cuckoo clock with great care

DjangoMOO's parser adds a few capabilities over the LambdaMOO original:

- **Object specifiers.** Object references can be prefixed with an
  article (`the`), a possessive marker (`my`), or another player's
  possessive form (`Bill's`). The parser uses the specifier to
  narrow the search scope before matching the name.
- **Multiple prepositions per command.** A single command can carry
  several preposition phrases — the example
  `put yellow bird in my cuckoo clock with great care` uses both
  `in` and `with`. Verbs can read each preposition's argument
  independently via `context.parser.get_pobj_str("in")` /
  `get_pobj_str("with")`, and a missing preposition raises a clean
  `NoSuchPrepositionError` without manual handling.
- **Intelligent tokenisation.** The lexer splits the command around
  known prepositions *before* word-splitting on spaces, so a
  preposition appearing inside a quoted string (`"bag of holding"`)
  doesn't accidentally split the argument. Quote-stripping and
  preposition recognition happen in the same pass.
- **Compound commands.** A single input line can carry multiple
  commands separated by `;`. Each segment runs through the full
  parser pipeline in order — useful when automating a setup
  sequence, scripting an agent's response to a token, or just
  chaining two related operations from one prompt. Errors in one
  segment do not stop the next.
- **`@`-prefix verb heads.** The first token of a command may begin
  with `@`. The lexer treats `@dig`, `@npc`, `@edit`, etc. as a
  single verb name — no special meaning attaches to the `@` itself,
  it's just an ordinary character in the verb name. The shipping
  verbs use it to flag administrative or world-building commands so
  they stand out from in-character verbs.
- **Case-insensitive verb dispatch.** Verb names match without
  regard to the case the player typed. `LOOK`, `look`, and `Look`
  all dispatch the same verb. Object and property names are matched
  case-insensitively too. This is documented elsewhere as well —
  the rule is single and uniform across every name the parser
  resolves.

This area was most influenced by the parser in Twisted Reality, the
MUD-like game Glyph and friends built a million years ago.

## Lexer

The first phase is lexical analysis. The `Pattern` class in
`moo/core/parse.py` runs a regex-based tokenisation pass that:

1. Splits the command into words on whitespace.
2. Honours double-quoted spans so multi-word names stay intact.
3. Identifies preposition tokens from `settings.PREPOSITIONS` and
   uses them to delimit direct-object and indirect-object phrases.

Quoting from the [LambdaMOO Programmer's Manual](https://www.hayseed.net/MOO/manuals/ProgrammersManual.html):

> The server next breaks up the command into words. In the simplest
> case, the command is broken into words at every run of space
> characters; for example, the command `foo bar baz` would be
> broken into the words `foo`, `bar`, and `baz`. To force the
> server to include spaces in a "word", all or part of a word can
> be enclosed in double-quotes. For example, the command
>
> `foo "bar mumble" baz" "fr"otz" bl"o"rt`
>
> is broken into the words `foo`, `bar mumble`, `baz frotz`, and
> `blort`. Finally, to include a double-quote or a backslash in a
> word, they can be preceded by a backslash, just like in MOO
> strings.

In DjangoMOO it's not usually necessary to quote object names that
contain spaces — the parser uses preposition boundaries to delimit
phrases, so `take wooden box` works without quotes. The exception
is when an object's name contains a *preposition word* (`my favorite
"bag of holding"`) — there, quoting is required to keep the
preposition from being treated as a phrase boundary.

The `Lexer` instance gets passed to a `Parser` along with a
reference to the calling user (the "caller"). For the full Lexer
attribute reference, see {doc}`../reference/parser`.

## Routing output back to the originating caller

When a verb teleports another object — say a wizard verb that moves a
player into a new room — the destination room's `enterfunc` and the
source room's `exitfunc` produce output. That output is routed back
to the *originating caller* (the player who typed the command), not
to the object being moved. The rule keeps wizards visible into the
side-effects of remote moves and prevents output from disappearing
into a disconnected NPC.

Verbs running inside `enterfunc` / `exitfunc` reach the originating
caller through `context.player`. `this` is the room and the moved
object is passed as the first argument.

## `$do_command` hook

Before the built-in parser runs, `interpret()` checks whether the
System Object (`#1`) defines a verb named `do_command`. If it does,
that verb is called with the tokenised command words as positional
`args`. The raw command line is accessible inside the verb as
`context.parser.command`.

If `do_command` returns a truthy value, the command is considered
fully handled and normal dispatch is skipped entirely. If it returns
a falsy value (or the verb does not exist), parsing continues
normally.

This is the standard LambdaMOO `$do_command` extension point —
useful for command logging, rate limiting, or routing commands to a
custom handler before the parser inspects them.

## See also

- {doc}`../reference/parser` — full reference: parser methods,
  preposition synonym groups, object-resolution rules, verb search
  order, and the last-match-wins dispatch rule.
- {doc}`../reference/verbs` — verb name asterisk grammar (`foo*bar`)
  and dispatch metadata.
- {doc}`../how-to/creating-verbs` — practical patterns for reading
  parser output from verb code.
