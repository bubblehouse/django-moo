# Celery Tasks

Every command, eval, or method-style verb call runs as a Celery task.
This page is the reference for the three task functions defined in
`moo.core.tasks`. For the verb-author entry points
(:func:`moo.sdk.invoke`, :func:`moo.sdk.set_task_perms`,
:func:`moo.sdk.task_time_low`, :func:`moo.sdk.schedule_continuation`),
see {doc}`builtins` and {doc}`../how-to/advanced-verbs`.

## Available tasks

```{eval-rst}
.. py:currentmodule:: moo.core.tasks
.. autofunction:: parse_command
.. autofunction:: parse_code
.. autofunction:: invoke_verb
```

`invoke_verb` is the only task verb authors interact with — and they
do that via the :func:`moo.sdk.invoke` helper rather than calling the
task directly. `invoke()` enforces wizard checks for `periodic=True`
and `cron=...` schedules and verifies that the caller has `execute`
on the target verb.

## Task isolation and limits

Each task runs as a separate Celery process. The isolation guarantees
are:

- **Process isolation.** A memory race or runaway loop in one verb
  cannot affect other concurrent tasks. Worker memory and CPU can be
  bounded by the OS.
- **Atomic database transaction.** Every verb invocation runs inside
  a Django `transaction.atomic()` block. An uncaught exception rolls
  back every database change made during the task.
- **Hard time limit.** The time budget is read from the
  `CELERY_TASK_TIME_LIMIT` environment variable in `moo/celeryconfig.py`
  (default `3` seconds). When the limit elapses, Celery terminates
  the worker process. Synchronous calls to other verbs share that
  budget — see {doc}`../how-to/advanced-verbs` for the time-aware
  continuation pattern that hands off remaining work to a fresh task.
- **RestrictedPython sandbox.** Verb source is compiled and executed
  inside Zope's RestrictedPython. Imports, builtins, and dunder
  attribute access are restricted; see {doc}`sandbox` for the full
  guard model.

## Inspecting the current task from verb code

`context.task_id` returns the Celery task ID for the running
invocation. `context.task_time` returns a `TaskTime(elapsed,
time_limit, remaining)` namedtuple — useful when you need to bail out
early before the worker kills the task. See {doc}`runtime` for the
full `context` reference.
