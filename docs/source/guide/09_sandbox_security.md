# Verb Sandbox Security

Verb code runs inside a restricted Python interpreter. This page describes how that restriction works, what it prevents, and what verb authors need to know when writing code.

## Why sandboxing is necessary

DjangoMOO is a multi-user system where programmer-level players can write and deploy verb code that runs on the server. An unrestricted Python interpreter would give any such user full access to the database, the file system, and the Django ORM — no permission system could protect against that. The sandbox exists to enforce the same permission model at the code level that the server already enforces at the command level.

The threat model is not anonymous users: unauthenticated players cannot write verbs. The concern is a legitimate programmer-level user who writes deliberately adversarial verb code, either to read data they should not see, modify objects they do not own, or escalate their own privileges.

Three layers of infrastructure already limit the blast radius before the sandbox even runs:

- Each verb executes inside a Celery worker process, isolated from the main web process.
- Every command execution runs inside a database transaction. If an exception is raised, the transaction rolls back, reverting any partial changes.
- Tasks run under a time limit enforced by Celery, which bounds both CPU abuse and accidental infinite loops.

The sandbox adds code-level restrictions on top of these.

## Execution environment

Verb source is compiled by `compile_verb_code()` in `moo/core/code.py` using RestrictedPython's `compile_restricted_function`. The compiled result is cached (LRU, 512 entries) keyed on the source text. Every verb is compiled with the signature:

    def verb(this, passthrough, _, *args, **kwargs): ...

Execution goes through `do_eval()`, which calls `r_exec()` or `r_eval()` with a controlled globals dict built by `get_restricted_environment()`. That dict replaces the standard Python builtins with a restricted subset and injects the custom attribute/item guards that RestrictedPython expects.

RestrictedPython transforms the source at compile time, rewriting:

- `obj.attr` attribute reads to call `_getattr_(obj, 'attr')`
- `obj.attr = val` attribute writes to call `_write_(obj).__setattr__('attr', val)`
- `obj[key]` subscript reads to call `_getitem_(obj, key)`
- `print(...)` to the print protocol (`_print_`)
- `x += y` to guarded in-place addition

This means every attribute and item access goes through functions we control, not CPython's raw `getattr`.

## Restricted builtins

`ALLOWED_BUILTINS` in `moo/settings/base.py` lists the only names from Python's standard builtins that verb code can call:

    ALLOWED_BUILTINS = (
        "dict",
        "enumerate",
        "getattr",
        "hasattr",
        "list",
        "set",
        "sorted",
    )

Everything else — including `type`, `dir`, `eval`, `exec`, `compile`, `open`, `vars`, `globals`, `locals`, `__import__` — is absent.

`type` is the most important exclusion. `type(obj).__mro__[-1].__subclasses__()` is the canonical Python sandbox escape: it walks up the inheritance hierarchy to `object`, then lists all subclasses currently loaded in the interpreter, which includes Django model classes. From there a caller can reach `Object.objects.all()` directly.

`dir` is unused in all verb code and returns dunder names that are useful for reconnaissance. `eval` and `exec` would allow dynamic code generation that bypasses compile-time restrictions.

`getattr` and `hasattr` are included but wrapped: the sandbox replaces them with versions that raise `AttributeError` for any name beginning with an underscore. This prevents `getattr(obj, '__class__')` from bypassing the `_getattr_` rewrite that RestrictedPython applies to the `.` syntax.

One historical artifact was also removed: the `__metaclass__=type` entry that Python 2 convention placed in the globals dict. It exposed `type` directly regardless of `ALLOWED_BUILTINS`.

## Module imports

`ALLOWED_MODULES` in `moo/settings/base.py` lists modules verb code may import:

    ALLOWED_MODULES = (
        "moo.core",
        "hashlib",
        "re",
        "datetime",
        "time",
    )

`restricted_import()` in `moo/core/code.py` enforces this list. Any import not in `ALLOWED_MODULES` raises `ImportError`.

### BLOCKED_IMPORTS

Even within an allowed module, specific names can be blocked. `BLOCKED_IMPORTS` is checked after the module is loaded; if the requested name appears in the block list for that module, the import is refused:

    BLOCKED_IMPORTS = {
        "moo.core": {
            "ContextManager",
            "_publish_to_player",
            "models",
            "acl",
            "auth",
            "object",
            "verb",
            "property",
            "moojson",
            "tasks",
            "code",
        },
    }

The submodule names (`models`, `acl`, etc.) are blocked because `from moo.core import models` would immediately expose `models.Object.objects.all()`, `models.User.objects.values("password")`, and `models.Verb.objects.update(code=...)` — full ORM access with no permission checks.

`ContextManager` is blocked because it exposes `override_caller()`, which can impersonate a wizard within a verb execution. `_publish_to_player` is blocked because it lacks a wizard check and its caller_id parameter is an escalation vector.

`exceptions` is intentionally not blocked. Verb code legitimately uses `from moo.core import exceptions` to catch `NoSuchObjectError`, `NoSuchVerbError`, and `NoSuchPropertyError`. That module contains only exception class definitions with no ORM access.

### Wizard-only modules

Wizards can import ORM model classes directly:

    WIZARD_ALLOWED_MODULES = (
        "moo.core.models.object",
        "moo.core.models.verb",
        "moo.core.models.property",
    )

`restricted_import()` checks `is_wizard()` on the current caller before allowing these.

### Removed modules

`string` was removed from `ALLOWED_MODULES`. `string.Formatter.get_field` calls CPython's real `getattr` internally — not the sandbox's guarded version — so `string.Formatter().get_field("0.__class__", [lookup(1)], {})` exposed `__class__` and from there the full ORM.

## Attribute and item access guards

`get_restricted_environment()` provides four guard functions that RestrictedPython calls for every attribute and item operation.

### Underscore attribute blocking

`safe_getattr(obj, name)` and `safe_hasattr(obj, name)` raise `AttributeError` for any name starting with `_`. This covers both the dotted syntax (`obj.__class__`) which RestrictedPython rewrites at compile time, and the builtin call form (`getattr(obj, '__class__')`) which the sandbox's wrapped `getattr`/`hasattr` intercepts.

### `str.format` and `str.format_map`

Both guards also raise `AttributeError` when `name in ("format", "format_map")` and `isinstance(obj, str)`. Python's C-level string formatting engine resolves attribute chains using the real `getattr` internally, so `'{0.__class__}'.format(obj)` would expose `__class__` on any object — including Django ORM instances from `lookup()`. Constructing the format string at runtime (`('{0.' + '__class__' + '}').format(obj)`) made static scanning useless. Blocking `format` and `format_map` on string instances closes this.

As a consequence, verb code must not call `str.format()`. Use f-strings or `str.replace()` instead:

    # Not allowed in verb code
    msg = "Hello {name}".format(name=player.title())

    # Use this instead
    msg = f"Hello {player.title()}"

    # Or for stored message templates with a placeholder
    msg = template.replace("{name}", player.title())

### Item access guards

`_write_.__setitem__` raises `KeyError` for any string key starting with `_`. The matching read-side guard `guarded_getitem(obj, key)` raises `KeyError` for the same. This prevents underscore keys from being written to or read from dicts in restricted code.

### The `_write_` class

`_write_(obj)` wraps an object for attribute writes. Its `__setattr__` raises `AttributeError` for underscore-prefixed names, and its `__setitem__` mirrors the key guard above. This means both `obj.__class__ = x` and `obj['__class__'] = x` are blocked.

### `safe_builtins` isolation

`get_restricted_environment()` builds `restricted_builtins = dict(safe_builtins)` as a local copy on each call. The original `safe_builtins` from RestrictedPython is a module-level singleton; mutating it in place would create a race window in concurrent workers where the real `getattr` could be momentarily visible.

## Context isolation

The `ContextManager` in `moo/core/code.py` stores per-execution state (caller, player, writer, parser, task_id) in Python `contextvars`, which are inherited by child tasks but isolated across concurrent executions in the same worker. Verb code accesses this via the `context` object exported from `moo.core`.

### `caller_stack` copy

`ContextManager.get("caller_stack")` returns `list(stack)` — a copy of the internal list, not the list itself. Returning the live list would allow verb code to call `context.caller_stack.append({"previous_caller": wizard_obj})`, poisoning the stack. When a wizard verb's `set_task_perms` finished and called `pop_caller()`, it would restore `_active_caller` to the injected wizard object.

### `_Context` as a data descriptor

The `_Context` class backing the `context` object uses data descriptors (both `__get__` and `__set__` defined). Non-data descriptors (only `__get__`) lose priority to instance attributes in Python's MRU. With a non-data descriptor, `_write_` could call `setattr(context, "caller", wizard_obj)` to shadow the contextvar-backed descriptor with an instance attribute. Since `context` is a module-level singleton shared within a Celery worker process, this would poison `context.caller.is_wizard()` for all subsequent tasks in that worker. Making it a data descriptor — where `__set__` raises `AttributeError` — closes this. `_Context.__setattr__` also raises `AttributeError` as defense-in-depth.

### `invoke()` guards

`invoke()` in `moo/core/__init__.py` has two security checks:

- `periodic=True` or `cron=...` requires the caller to be a wizard. Non-wizards could otherwise create unlimited `IntervalSchedule` and `PeriodicTask` database rows, flooding the Celery beat schedule.
- All invocations check `exec_obj.can_caller("execute", verb)`. `Object.invoke_verb()` enforces this too, but `invoke()` accepted raw `Verb` objects and previously bypassed it, allowing a caller with only `read` access to enqueue any verb.

### `set_task_perms`

`set_task_perms()` raises `UserError` for non-wizards. This was enforced before the audit; a regression test was added to prevent it from being silently removed.

## Model-level permission checks

Even with all import and attribute guards in place, verb code can obtain Django model instances through indirect means. For example, `obj.properties` is a `RelatedManager` — its name has no underscore, so `_getattr_` allows access. Via `obj.properties.filter(name='x').first()`, verb code can obtain a `Property` instance directly, bypassing the permission-checked `obj.get_property()` path.

To close this, the model `save()` and `delete()` methods enforce permissions as the last line of defense:

- `Verb.save()` calls `self.origin.can_caller("write", self)` before `super().save()` for any update (`self.pk is not None`).
- `Property.save()` calls `self.origin.can_caller("write", self)` before `super().save()` for updates.
- `Object.delete()` calls `self.can_caller("write", self)` as its first action.

These checks mean that even if verb code obtains a model instance through an unguarded path, persisting changes still requires the caller to hold `write` permission on the owning object.

## Known gap: `dict.update()` and underscore keys

`dict.update({'__class__': x})` inserts underscore keys at the C level, bypassing `_write_.__setitem__`. Those keys can then be retrieved via `dict.get()`, `.items()`, or `.values()`, bypassing `guarded_getitem`. Standalone exploitability is low — with `str.format`/`format_map` blocked, there is no obvious way to turn an underscore key in a plain dict into ORM access. The inconsistency is documented in `test_dict_update_bypasses_write_guard` in `moo/core/tests/test_security.py`. Closing it fully would require subclassing `dict`, which risks breaking legitimate verb code that passes dicts to standard library functions.

## Writing safe verb code

A few patterns to avoid in verb code, and what to use instead:

**String formatting.** `str.format()` and `str.format_map()` are blocked. Use f-strings for dynamic content and `str.replace()` for stored message templates with named slots.

**Property access.** `has_property(name)` followed by `get_property(name)` is two queries. Use `get_property` inside a `try`/`except NoSuchPropertyError` block:

    from moo.core import exceptions

    try:
        desc = this.get_property("description")
    except exceptions.NoSuchPropertyError:
        desc = "You see nothing special."

**Attribute access.** Dotted access via `__getattr__` on an `Object` costs two queries (verb miss + property lookup). Assign to a local variable if the value is used more than once:

    dest = this.get_property("dest")
    # use dest, not this.dest, for the rest of the verb

**Dunder attributes.** Any attribute name beginning with `_` will raise `AttributeError`. Do not attempt to access `__class__`, `__dict__`, `__module__`, or any other dunder on objects in verb code.

**Underscore dict keys.** Setting or reading dict keys that begin with `_` will raise `KeyError`. This is rarely needed in practice.

## Security regression tests

`moo/core/tests/test_security.py` contains 37 tests that document every sealed escape vector. Each test corresponds to a specific attack path: the test name, the attack vector it covers, and whether the vector is closed or documented-but-open are all visible in the file. Run these tests after any change to `moo/core/code.py`, `moo/settings/base.py`, or any of the model `save()`/`delete()` methods to confirm the sandbox remains intact.
