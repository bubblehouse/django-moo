# Verb Sandbox Security Reference

For background on why the sandbox exists and how the execution environment works, see {doc}`../explanation/sandbox`.

## Restricted builtins

`ALLOWED_BUILTINS` in `moo/settings/base.py` lists the only names from Python's standard builtins that verb code can call:

    ALLOWED_BUILTINS = (
        "all",
        "any",
        "dict",
        "enumerate",
        "getattr",
        "hasattr",
        "list",
        "max",
        "min",
        "PermissionError",
        "set",
        "sorted",
        "sum",
    )

Everything else — including `type`, `dir`, `eval`, `exec`, `compile`, `open`, `vars`, `globals`, `locals`, `__import__` — is absent.

`type` is the most important exclusion. `type(obj).__mro__[-1].__subclasses__()` is the canonical Python sandbox escape: it walks up the inheritance hierarchy to `object`, then lists all subclasses currently loaded in the interpreter, which includes Django model classes. From there a caller can reach `Object.objects.all()` directly.

`dir` is unused in all verb code and returns dunder names that are useful for reconnaissance. `eval` and `exec` would allow dynamic code generation that bypasses compile-time restrictions.

`getattr` and `hasattr` are included but wrapped: the sandbox replaces them with versions that raise `AttributeError` for any name beginning with an underscore. This prevents `getattr(obj, '__class__')` from bypassing the `_getattr_` rewrite that RestrictedPython applies to the `.` syntax.

One historical artifact was also removed: the `__metaclass__=type` entry that Python 2 convention placed in the globals dict. It exposed `type` directly regardless of `ALLOWED_BUILTINS`.

## Module imports

`ALLOWED_MODULES` in `moo/settings/base.py` lists modules verb code may import:

    ALLOWED_MODULES = (
        "moo.sdk",
        "hashlib",
        "re",
        "datetime",
        "time",
    )

`restricted_import()` in `moo/core/code.py` enforces this list. Any import not in `ALLOWED_MODULES` raises `ImportError`.

### BLOCKED_IMPORTS

Even within an allowed module, specific names can be blocked. `BLOCKED_IMPORTS` is checked after the module is loaded; if the requested name appears in the block list for that module, the import is refused:

    BLOCKED_IMPORTS = {
        "moo.sdk": {
            "ContextManager",
        },
    }

`moo.core` is not in `ALLOWED_MODULES` at all — verb code cannot reach Django ORM model classes (`Object.objects`, `User.objects`, etc.) or internal framework machinery.

`ContextManager` is blocked from `moo.sdk` because it exposes `override_caller()`, which can impersonate a wizard within a verb execution. `_publish_to_player` is not exposed by `moo.sdk` (it remains internal to `moo.core`).

`NoSuchObjectError`, `NoSuchVerbError`, and `NoSuchPropertyError` are directly available in `moo.sdk.__all__` — import them with `from moo.sdk import NoSuchObjectError` etc.

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

`get_restricted_environment()` provides guard functions that RestrictedPython calls for every attribute and item operation. There are two parallel attribute guards:

- `get_protected_attribute(obj, name)` is installed as `_getattr_`. RestrictedPython rewrites every dotted read (`obj.attr`) to call this function at compile time.
- `safe_getattr(obj, name, *args)` replaces the builtin `getattr`. Both functions apply the same rules; the duplication is necessary because the builtin `getattr(obj, name)` call form is not rewritten by the RestrictedPython compiler.

### Underscore attribute blocking

Both guards raise `AttributeError` for any name starting with `_`. This covers both the dotted syntax (`obj.__class__`) which RestrictedPython rewrites at compile time, and the builtin call form (`getattr(obj, '__class__')`) which the wrapped `getattr`/`hasattr` intercepts.

`safe_hasattr(obj, name)` returns `False` for underscore names rather than raising, matching the documented behavior of the builtin `hasattr`.

### `str.format` and `str.format_map`

Both guards also raise `AttributeError` when `name in ("format", "format_map")` and `isinstance(obj, str)`. Python's C-level string formatting engine resolves attribute chains using the real `getattr` internally, so `'{0.__class__}'.format(obj)` would expose `__class__` on any object — including Django ORM instances from `lookup()`. Constructing the format string at runtime (`('{0.' + '__class__' + '}').format(obj)`) made static scanning useless. Blocking `format` and `format_map` on string instances closes this.

As a consequence, verb code must not call `str.format()`. Use f-strings or `str.replace()` instead:

    # Not allowed in verb code
    msg = "Hello {name}".format(name=player.title())

    # Use this instead
    msg = f"Hello {player.title()}"

    # Or for stored message templates with a placeholder
    msg = template.replace("{name}", player.title())

### QuerySet and BaseManager restrictions

Both guards check `isinstance(obj, (QuerySet, BaseManager))` and allow only the names in `_QUERYSET_ALLOWED`:

    _QUERYSET_ALLOWED = frozenset({
        "all", "filter", "exclude",
        "first", "last", "get",
        "exists", "count", "contains",
        "order_by", "distinct", "none",
        "select_related", "prefetch_related",
    })

Every other method or attribute on a QuerySet or manager instance raises `AttributeError`. This covers:

- Bulk mutation methods: `update()`, `delete()`, `create()` — which issue SQL directly, bypassing the model `save()`/`delete()` permission hooks.
- `values()` and `values_list()` — which return plain dicts whose `"value"` keys are not `Property` instances, so the `Property.value` read guard would not fire.
- `add()` and `remove()` on ManyToMany managers — which issue SQL directly, bypassing ACL checks on the owning object.
- `model` — which exposes the raw Django model class, opening the path to `Object.objects.all()`.
- All async variants (`adelete`, `aupdate`, `acreate`, etc.) and any future Django additions are blocked by default unless explicitly added to `_QUERYSET_ALLOWED`.

`select_related()` and `prefetch_related()` are allowed because they are actively used by verb code and return a new QuerySet of the same type — the instances they produce still go through the attribute guards when accessed.

### `acl` and `value` attribute guards

Both guards include two additional permission checks:

- Accessing `acl` on any `AccessibleMixin` instance calls `obj.can_caller("grant", obj)`. The `acl` attribute is a RelatedManager — without this check, verb code could enumerate ACL entries and read permission rules they should not know about.
- Accessing `value` on a `Property` instance calls `obj.origin.can_caller("read", obj)`. This ensures that obtaining a `Property` object via `obj.properties.filter(...).first()` does not bypass the permission-checked `obj.get_property()` path.

### Module traversal blocking

Both guards check attribute accesses on `ModuleType` instances to prevent walking across module boundaries. When a dotted access on a module returns another module, that nested module must appear in `ALLOWED_MODULES` or `WIZARD_ALLOWED_MODULES`; otherwise `AttributeError` is raised. The `BLOCKED_IMPORTS` table is also checked — names blocked from import are equally blocked from attribute access on the module object, closing the `import moo.sdk; moo.sdk.ContextManager` path.

### Item access guards

`_write_.__setitem__` raises `KeyError` for any string key starting with `_`. The matching read-side guard `guarded_getitem(obj, key)` raises `KeyError` for the same. This prevents underscore keys from being written to or read from dicts in restricted code.

### The `_write_` class

`_write_(obj)` wraps an object for attribute writes. Its `__setattr__` calls `set_protected_attribute(obj, name, value)`, which raises `AttributeError` for underscore-prefixed names and, for any `AccessibleMixin` instance, calls `obj.can_caller("write", obj)` before setting the attribute. Its `__setitem__` mirrors the key guard. This means both `obj.__class__ = x` and `obj['__class__'] = x` are blocked, and any attribute write to an object the caller does not own raises an access error.

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

To close this, the model `save()`, `delete()`, and `__call__()` methods enforce permissions as the last line of defense:

- `Verb.save()` calls `self.origin.can_caller("write", self)` before `super().save()` for both creates (`self.pk is None`) and updates.
- `Property.save()` calls `self.origin.can_caller("write", self)` before `super().save()` for updates.
- `Object.delete()` calls `self.can_caller("write", self)` as its first action.
- `Verb.__call__()` calls `self.origin.can_caller("execute", self)` when an active session is present. Obtaining a `Verb` instance via `obj.verbs.filter(...).first()` and calling it directly would otherwise bypass the execute-permission check that `invoke_verb()` performs. The `passthrough()` builtin passes `_bypass_execute_check=True` to skip this redundant check when a parent verb has already been authorized.

These checks mean that even if verb code obtains a model instance through an unguarded path, persisting changes or executing verbs still requires the caller to hold the appropriate permission on the owning object.

## Known gap: `dict.update()` and underscore keys

`dict.update({'__class__': x})` inserts underscore keys at the C level, bypassing `_write_.__setitem__`. Those keys can then be retrieved via `dict.get()`, `.items()`, or `.values()`, bypassing `guarded_getitem`. Standalone exploitability is low — with `str.format`/`format_map` blocked, there is no obvious way to turn an underscore key in a plain dict into ORM access. The inconsistency is documented in `test_dict_update_bypasses_write_guard` in `moo/core/tests/test_security_sandbox.py`. Closing it fully would require subclassing `dict`, which risks breaking legitimate verb code that passes dicts to standard library functions.

## Writing safe verb code

A few patterns to avoid in verb code, and what to use instead:

**String formatting.** `str.format()` and `str.format_map()` are blocked. Use f-strings for dynamic content and `str.replace()` for stored message templates with named slots.

**Property access.** `has_property(name)` followed by `get_property(name)` is two queries. Use `get_property` inside a `try`/`except NoSuchPropertyError` block:

    from moo.sdk import NoSuchPropertyError

    try:
        desc = this.get_property("description")
    except NoSuchPropertyError:
        desc = "You see nothing special."

**Attribute access.** Dotted access via `__getattr__` on an `Object` costs two queries (verb miss + property lookup). Assign to a local variable if the value is used more than once:

    dest = this.get_property("dest")
    # use dest, not this.dest, for the rest of the verb

**Dunder attributes.** Any attribute name beginning with `_` will raise `AttributeError`. Do not attempt to access `__class__`, `__dict__`, `__module__`, or any other dunder on objects in verb code.

**Underscore dict keys.** Setting or reading dict keys that begin with `_` will raise `KeyError`. This is rarely needed in practice.

## Security regression tests

The security tests are split across six files, each covering a distinct area:

| File | Tests | Coverage |
|------|-------|----------|
| `test_security_builtins.py` | 13 | Restricted builtins: `type`, `dir`, `eval`, `exec`, dunder access via `getattr`/`hasattr`, `str.format`/`format_map` |
| `test_security_imports.py` | 9 | Module imports: allowed/blocked modules, `BLOCKED_IMPORTS`, wizard-only modules, `string.Formatter` removal, module traversal |
| `test_security_sandbox.py` | 9 | Core sandbox: underscore attribute blocking, `_write_` class, dict key guards, `__metaclass__` removal, `safe_builtins` isolation |
| `test_security_context.py` | 9 | Context isolation: `caller_stack` copy, `_Context` data descriptor, `set_task_perms` non-wizard rejection, `invoke()` guards |
| `test_security_models.py` | 21 | Model permissions: `Verb.save()`, `Property.save()`, `Object.delete()`, RelatedManager paths, `Verb.__call__()` execute check |
| `test_security_queryset.py` | 14 | QuerySet/BaseManager: mutation methods, `values()`, M2M `add()`, `model` attribute, `Property.value` guard, ACL enumeration guard, `select_related()` safety |

75 tests total. Each test corresponds to a specific attack path; the test name and docstring describe the vector and whether it is closed or documented-but-open. Run the full suite after any change to `moo/core/code.py`, `moo/settings/base.py`, or any model `save()`/`delete()`/`__call__()` method.
