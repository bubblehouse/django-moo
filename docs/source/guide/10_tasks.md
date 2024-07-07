## MOO Tasks

Each task in the DjangoMOO environment is executed asynchronously by the Celery workers.

### Available Tasks

```{eval-rst}
.. py:currentmodule:: moo.core.tasks
.. autofunction:: parse_command
.. autofunction:: parse_code
.. autofunction:: invoke_verb
```

### Task Security

The running of a task is kept reasonably secure and isolated in a few ways:

* Each Verb execution runs in a Celery worker; if a memory race is triggered,
  it's limited to the worker process, which **CAN** be limited by Unix process management.
* Before Verb execution, a new atomic DB transaction is started. This **SHOULD** prevent
  conflicts when two Verbs are trying to modify the same object.
* Verb runtime itself is limited to 3 seconds (configurable). This **SHOULD** force the Verb
  to complete in order to commit the changes to the database.
* Verbs are compiled and executed inside a restricted environment created by Zope's `RestrictedPython`
  library. Only selected imports and builtins are allowed, and access to `_` variables is restricted.

### Executing Statements at a Later Time

But if you're limited to 3 seconds in a Verb, how do you create longer tasks? The key is to
compose your function into multiple Verb calls, which you can invoke asynchronously using the
`invoke()` function:

```{eval-rst}
.. py:currentmodule:: moo.core
.. autofunction:: invoke
```

Using `invoke()` let's create a bad example of a talking parrot:

```python
from moo.core import api, invoke
if api.parser is not None:
    invoke(api.parser.verb, delay=30, periodic=True)
    return
for obj in api.caller.location.filter(player__isnull=False):
    write(obj, "A parrot squawks.")
```

Right now it's just repeating every thirty seconds, but we can make it slightly more intelligent
by handling our own repeating Verbs:

```python
from moo.core import api, invoke
if api.parser is not None:
    invoke(api.parser.verb, delay=30, value=0)
    return
value = kwargs['value'] + 1
for obj in api.caller.location.filter(player__isnull=False):
    write(obj, f"A parrot squawks {value}.")
invoke(api.parser.verb, delay=30, value=value)
```

Let's say we didn't want to handle writing ourselves (we shouldn't) and wanted instead
to re-use the `say` Verb.

```python
from moo.core import api, invoke
if api.parser is not None:
    say = api.caller.get_verb('say', recurse=True)
    invoke(verb=api.parser.verb, callback=say, delay=30, value=0)
    return
value = kwargs['value'] + 1
return f"A parrot squawks {value}."
```
