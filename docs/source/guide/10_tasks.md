## MOO Tasks

Each task in the DjangoMOO environment is executed asynchronously by the Celery workers.

### Available Tasks
```{eval-rst}
.. py:currentmodule:: moo.core.tasks
.. autofunction:: parse_command
.. autofunction:: parse_code
```

### Task Security

The running of a task is kept reasonably secure and isolated in a few ways:

* Each Verb execution runs in a Celery worker; if a memory race is triggered,
  it's limited to the worker process, which **CAN** be limited by Unix process management.
* Before Verb execution, a new atomic DB transaction is started. This **SHOULD** prevent
  conflicts when two Verbs are trying to modify the same object.
* Verb runtime itself is limited to 3 seconds (configurable). This **SHOULD** force the Verb
  to complete in order to commit the changes to the database.

### Executing Statements at a Later Time

But if you're limited to 3 seconds in a Verb, how do you create longer tasks? The key is to
compose your function into multiple Verb calls, which you can invoke asynchronously using the
Task class:

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoclass:: Task
```
