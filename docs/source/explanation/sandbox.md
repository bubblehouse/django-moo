# Why the Verb Sandbox Exists

Verb code runs inside a restricted Python interpreter. This page explains why that restriction exists and how the execution environment is structured. For the technical details of what is restricted and how to write safe verb code, see {doc}`../reference/sandbox`.

## Why sandboxing is necessary

DjangoMOO is a multi-user system where programmer-level players can write and deploy verb code that runs on the server. An unrestricted Python interpreter would give any such user full access to the database, the file system, and the Django ORM — no permission system could protect against that. The sandbox exists to enforce the same permission model at the code level that the server already enforces at the command level.

The threat model is not anonymous users: unauthenticated players cannot write verbs. The concern is a legitimate programmer-level user who writes deliberately adversarial verb code, either to read data they should not see, modify objects they do not own, or escalate their own privileges.

Four layers of infrastructure already limit the blast radius before the sandbox's compile-time rewrites even run:

- Each verb executes inside a Celery worker process, isolated from the main web process.
- Every command execution runs inside a database transaction. If an exception is raised, the transaction rolls back, reverting any partial changes.
- Tasks run under a time limit enforced by Celery, which bounds both CPU abuse and accidental infinite loops.
- The model layer enforces permissions on every `save()`, `delete()`, and verb `__call__()`. Even if verb code reaches a Django model instance through an unguarded path, persisting changes still requires the caller to hold the appropriate permission on the owning object.

The sandbox adds code-level restrictions on top of these.

## Execution environment

Verb source is compiled by `compile_verb_code()` in `moo/core/code.py` using RestrictedPython's `compile_restricted_function`. The compiled result is cached (LRU, 512 entries) keyed on the source text. Every verb is compiled with the signature:

    def verb(this, passthrough, _, *args, **kwargs): ...

Execution goes through `do_eval()`, which calls `r_exec()` or `r_eval()` with a controlled globals dict built by `get_restricted_environment()`. That dict replaces the standard Python builtins with a restricted subset and injects the custom attribute/item guards that RestrictedPython expects.

RestrictedPython transforms the source at compile time, rewriting:

- `obj.attr` attribute reads to call `_getattr_(obj, 'attr')`
- `obj.attr = val` attribute writes to call `_write_(obj).__setattr__('attr', val)`
- `obj[key]` subscript reads to call `_getitem_(obj, key)`
- `obj[key] = val` subscript writes to call `_write_(obj).__setitem__(key, val)`
- `print(...)` to the print protocol (`_print_`)
- `x += y` to guarded in-place addition

This means every attribute and item access goes through functions we control, not CPython's raw `getattr`.

## See also

- {doc}`../reference/sandbox` — the full enforcement detail: the
  attribute/item guards, the `_write_` class, QuerySet method
  whitelist, the `str.format` block, model-layer permission checks,
  and security regression tests.
- {doc}`../reference/permissions` — the named permissions and where
  each is enforced at the model layer.
