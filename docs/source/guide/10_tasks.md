## MOO Tasks

Each task in the DjangoMOO environment is executed asynchronously by the Celery workers.

### Available Tasks

Most of these tasks aren't used by Verb code, the exception is `invoke_verb` which is actually
callable via the `moo.core.invoke` function.

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

