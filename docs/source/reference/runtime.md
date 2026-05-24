# The DjangoMOO Runtime

DjangoMOO verb code runs inside a RestrictedPython sandbox with a
constrained runtime environment. This page documents the global names
available to a verb, the `context` object, and the execution-environment
limits the sandbox enforces. For the conceptual model and full set of
sandbox guards, see {doc}`sandbox`.

## Names available in every verb

Six names are injected into the verb's local scope by the compiler.
Linters will flag them as undefined — add a
`# pylint: disable=undefined-variable` at the top of every verb file.

| Name | Type | Description |
|------|------|-------------|
| `this` | `Object` | The object the verb was matched on. With `--dspec this`, this is the direct object. With `--dspec any` or `none`, this is the caller. |
| `passthrough` | callable | Calls the same verb on the next ancestor up the parent chain (the MOO `super()`). Pass any received args through: `passthrough(*args, **kwargs)`. |
| `_` | `Object` | The System Object (`pk=1`). Used for `_.string_utils`, `_.gripe_recipients`, and other globals. The single attribute name beginning with `_` that the sandbox allows. |
| `args` | `list` | Positional arguments when the verb is invoked as a method. Empty when invoked from the command parser. |
| `kwargs` | `dict` | Keyword arguments when invoked as a method. Empty from the parser. |
| `verb_name` | `str` | The exact alias the caller used to invoke the verb. **Never assign to a local named `verb_name`** — Python scoping makes the whole function treat it as a local, and reads before the assignment raise `UnboundLocalError`. |

## The `context` object

`from moo.sdk import context` exposes a module-level proxy whose
attributes track the state of the currently executing session. The
proxy is implemented over `contextvars.ContextVar`, so each Celery
task gets its own isolated copy.

When a player sends a command, the task runner opens a
`ContextManager` scope:

```python
with code.ContextManager(caller, output.append, task_id=task_id) as ctx:
    parse.interpret(ctx, line)
```

`parse.interpret` then attaches a `Parser` instance, making the full
session state available to whatever verb dispatches.

### Attributes

```{eval-rst}
.. py:currentmodule:: moo.sdk.context
.. autoattribute:: _Context.player
.. autoattribute:: _Context.caller
.. autoattribute:: _Context.parser
.. autoattribute:: _Context.writer
.. autoattribute:: _Context.task_id
.. autoattribute:: _Context.task_time
.. autoattribute:: _Context.caller_stack
```

`context.player` and `context.caller` are the same object at the start
of a command. They diverge as verbs invoke other verbs: `caller` shifts
to the new executor, while `player` stays the original session
initiator. See {doc}`../how-to/permissions` for why this matters.

## Execution environment

Verb code is compiled by RestrictedPython and executed inside a
controlled globals dict. Practical effects on what verb code can do:

- The `print()` builtin routes through `context.writer` and ends up on
  the initiator's connection. Output is buffered for the duration of
  the verb task; consecutive `print(..., end="")` calls are coalesced
  into one writer invocation so a verb can stream a phrase with
  multiple calls without producing fragmented lines on the client.
- Attribute names beginning with `_` raise `AttributeError` (the global
  `_` reference to the System Object is the single allowed exception).
- Augmented assignment to a *subscript* (`d["k"] += 1`) is rejected —
  use a plain variable instead. Augmented assignment on locals
  (`x += 1`) works.
- Only the builtins in `settings.ALLOWED_BUILTINS` are available
  (`all`, `any`, `dict`, `enumerate`, `getattr`, `hasattr`, `list`,
  `max`, `min`, `set`, `sorted`, `sum`, `PermissionError`).
- Only the modules in `settings.ALLOWED_MODULES` may be imported
  (`moo.sdk`, `hashlib`, `re`, `datetime`, `time`). Wizard-owned
  verbs additionally get `moo.core.models.{object,verb,property}`.
- `return` may appear at any depth in the verb body, not just at
  function end.
- Each verb invocation finishes within `settings.CELERY_TASK_TIME_LIMIT`
  (default 3 seconds) or the worker terminates the task. Synchronous
  calls to other verbs share that budget.

For the full sandbox model — including model-layer permission checks,
QuerySet method whitelists, and the `str.format` block — see
{doc}`sandbox`.

## Looking up objects

There is no LambdaMOO-style `#N` literal syntax in Python. To
obtain an object reference inside verb code, use `lookup()`:

```{eval-rst}
.. py:currentmodule:: moo.sdk
.. autofunction:: moo.sdk.lookup
   :no-index:
```

`lookup()` accepts an object PK, an exact `name`, or any of an
object's aliases. It raises `NoSuchObjectError` if nothing matches —
that exception is a `UserError` and propagates cleanly to the player
when uncaught (see {doc}`../how-to/creating-verbs`).
