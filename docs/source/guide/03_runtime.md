# The DjangoMOO Runtime

Like LambdaMOO, only certain kinds of data can appear in a DjangoMOO database and those are the objects MOO programs ("Verbs") can manipulate. Besides the typical set of Python primitives, the other types of values include :class:`.Object`, :class:`.Property` and :class:`.Verb`. Note the slight overlap between the built-in python class :class:`.object` and our ORM model :class:`.Object`

## Python Value Types and the restricted environment

Technically, a Verb can use any kind of Python value, but since all MOO code is run in a restricted Python environment, there are a number of limitations to consider:

* the `print()` built-in function sends output to the current player
* access to attributes beginning with underscores is disabled
  * with the notable exception of the `_` reference to the System Object
* in-place variable modification is disabled
* only the builtins in `ALLOWED_BUILTINS` are available
* only the modules in `ALLOWED_IMPORTS` may be imported
* total runtime cannot exceed `CELERY_TASK_TIME_LIMIT` (default 3 seconds)
  * if a verb calls another verb as a method, the total runtime cannot exceed `CELERY_TASK_TIME_LIMIT`
* a verb can use `return` at any time

There's no equivalent concept to the LambdaMOO object notation, the only way to fetch object references is via the Python API:



```{eval-rst}
.. autofunction:: moo.core.lookup()
   :no-index:
```

## The DjangoMOO `context` Variable

`context` is a module-level proxy object that exposes the state of the currently executing MOO session. It is implemented as a thin wrapper around Python's `contextvars.ContextVar`, making it safe for concurrent async/Celery execution — each task gets its own isolated copy.

When a player sends a command, the Celery task in `tasks.py` opens a `ContextManager` scope:

```python
with code.ContextManager(caller, output.append, task_id=task_id) as ctx:
    parse.interpret(ctx, line)
```

`parse.interpret` then attaches a `Parser` instance, making the full session state available. Verb code runs inside this scope.

### Attributes Available in Verb Code

| Attribute | Type | Description |
|---|---|---|
| `context.player` | `Object` | The player who issued the command — the original session initiator. **Use this for "who is acting" logic.** |
| `context.caller` | `Object` | The object whose verb code is currently executing. Changes as verbs call other verbs. |
| `context.parser` | `Parser` | The parsed command. Provides `get_dobj()`, `get_dobj_str()`, `get_pobj_str(prep)`, etc. |
| `context.caller_stack` | `list` | Stack of caller frames accumulated as verbs invoke sub-verbs. Useful for permission auditing. |
| `context.task_id` | `str` | The Celery task ID for the current session. |

### Typical Usage in a Verb

```python
from moo.sdk import context

player = context.player               # who sent the command
target = context.parser.get_dobj()   # the direct object
msg = context.parser.get_pobj_str("with")  # a prepositional argument
```

### Key Distinction: `player` vs `caller`

At command parsing time, `context.player` and `context.caller` are the same object. They diverge as verbs are called, and when a verb on one object invokes a verb on another: `context.caller` shifts to the new executor, while `context.player` remains anchored to the original session initiator.
