# Verbs on Objects

A **verb** is a named MOO program attached to an Object. Most verbs
implement player commands — `look`, `take`, `drop`, `say` — but verbs
can also be invoked as methods from other verb code (`obj.title()`,
`this.moveto(...)`). Verb authoring as a craft is covered in
{doc}`../tutorials/first-verb` and {doc}`../how-to/creating-verbs`;
this page is the reference for the `Verb` model and its dispatch
metadata.

## Identity and lifecycle

Each `Verb` row has an `origin` (the Object the verb is attached to),
one or more `Name` aliases, source code, and optional dispatch metadata
(`direct_object`, `indirect_objects`). A verb is deleted when its
origin object is destroyed.

At dispatch time, the parser searches caller → inventory → location →
dobj → pobj for a matching verb on each object, with last match
winning. See {doc}`parser` for the full search order and
verb-resolution rules.

## Verb attributes

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Verb.pk

    The unique identifying number of this Verb.

.. autoattribute:: Verb.code
   :no-index:
.. autoattribute:: Verb.repo
   :no-index:
.. autoattribute:: Verb.filename
   :no-index:
.. autoattribute:: Verb.ref
   :no-index:
.. autoattribute:: Verb.owner
   :no-index:
.. autoattribute:: Verb.origin
   :no-index:
.. autoattribute:: Verb.direct_object
   :no-index:
.. autoattribute:: Verb.indirect_objects
   :no-index:
```

`direct_object` is one of `this`, `any`, `none`, or `either`.
`indirect_objects` is a ManyToMany of `(preposition, specifier)`
pairs. Both are populated from the verb file's shebang at load time.

## Verb names

A single Verb row may have multiple `Name` aliases stored as separate
rows. The shebang `#!moo verb @reload reload_batch` creates one
`Verb` with two `Name`s, so any of `@reload` or `reload_batch` will
match. `verb_name` inside the verb body holds the specific alias the
caller used.

Names support a single asterisk for prefix matching:

| Pattern | Matches |
|---------|---------|
| `foo` | `foo` only (exact match). |
| `foo*bar` | `foo`, `foob`, `fooba`, `foobar` (any prefix of `foobar` at least as long as `foo`). |
| `foo*` | Any string starting with `foo` — `foo`, `food`, `foobar`. |
| `*` | Anything. |

The asterisk itself is not part of the matched string.

## Dispatch metadata

Argument-specifier semantics:

| `direct_object` | Effect |
|-----------------|--------|
| `none` (default) | Verb fires only when the command has no direct object. |
| `any` | A direct object must be present; any string is accepted. |
| `this` | Verb fires only when the parsed direct object resolves to `origin`. |
| `either` | Direct object is optional. `this` is set correctly when one is given. |

`indirect_objects` is a list of preposition/specifier pairs. The
preposition canonical forms (`with`, `at`, `in`, `on top of`, etc.)
and their synonym groups live in `settings.PREPOSITIONS`; see
{doc}`parser` for the full table. Each specifier is `none`, `any`,
or `this` (matching the `direct_object` semantics above).

For the shebang grammar that populates these fields, see
{doc}`../how-to/creating-verbs`.

## Permissions

| Permission | Effect |
|------------|--------|
| `read` | Read the verb's source code and metadata |
| `write` | Modify the verb's source, dispatch metadata, or names |
| `execute` | Invoke the verb |
| `entrust` | Change the verb's owner |
| `grant` | Set permissions on the verb |
| `anything` | Wildcard — all of the above |

These checks fire automatically:

- `Verb.save()` on a new row checks `write` on the `origin` Object.
  On an update it checks `write` on the verb itself, plus `entrust`
  if the owner is changing.
- `Verb.delete()` checks `write` on the verb.
- `Verb.__call__()` checks `execute` on the verb when there's an
  active session. `passthrough()` passes `_bypass_execute_check=True`
  internally so a parent verb call doesn't pay the check twice.

`add_verb()` requires `develop` permission on the target object —
that's the gate for adding a new verb to an object you don't own.

Verb code does not need to check permissions before invoking another
verb or modifying a property; the model layer raises `AccessError`
on failure and the task runner shows it as a clean error to the
player. See {doc}`../how-to/permissions`.

## Error handling

When a verb raises an exception:

- **`UserError` and subclasses** (including `NoSuchObjectError`,
  `NoSuchVerbError`, `NoSuchPropertyError`, `UsageError`,
  `QuotaError`) — the exception's message is shown to the player as
  a bold red line. Verbs should raise these rather than printing
  errors manually.
- **`PermissionError` (including `AccessError`)** — same UX as
  `UserError`; the message is the model-layer guard's "X is not
  allowed to 'Y' on Z" string.
- **Any other exception** — regular players see
  `"An error occurred while executing the command."`; wizards see
  the full traceback.

Because errors propagate cleanly, parser methods like `get_dobj()`
can be called without defensive wrapping. If the named object
doesn't exist, `NoSuchObjectError` bubbles up and the player sees
`"There is no 'X' here."` automatically. Catch only when you want
a different message or alternative behaviour.

## See also

- {doc}`../tutorials/first-verb` — write your first verb.
- {doc}`../how-to/creating-verbs` — shebang grammar, parser
  methods, output mechanisms, error handling.
- {doc}`../how-to/advanced-verbs` — calling other verbs,
  `passthrough()`, time-aware continuation.
- {doc}`parser` — verb search order, preposition synonym groups,
  the verb-name asterisk grammar.
- {doc}`builtins` — `Object.add_verb()`, `Object.get_verb()`,
  `Object.invoke_verb()` signatures.
