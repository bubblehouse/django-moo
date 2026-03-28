# Audit History

Seventeen passes, 50 holes sealed, 644 tests (3 skipped). This file is the canonical in-repo record. The project memory file (`~/.claude/projects/-Users-philchristensen-Workspace-bubblehouse-django-moo/memory/project_security_audit.md`) mirrors this content — keep both in sync after each pass.

---

## Pass 1 — 6 holes sealed

1. **`type()` removed from `ALLOWED_BUILTINS`** — `type(obj).__mro__[-1].__subclasses__()` is the canonical Python sandbox escape.
2. **`getattr()`/`hasattr()` wrapped to block underscore names** — `getattr(obj, '__class__')` bypassed the `_getattr_` guard entirely.
3. **`dir()` removed from `ALLOWED_BUILTINS`** — unused in verb code; returned dunder names for reconnaissance.
4. **`__metaclass__=type` removed from env dict** — Python 2 artifact that exposed `type` directly in globals.
5. **`ContextManager` blocked via `BLOCKED_IMPORTS`** — `ContextManager.override_caller(wizard_obj)` was a wizard impersonation path via `from moo.core import ContextManager`.
6. **`set_task_perms` wizard check confirmed** — non-wizards already raised `UserError`; regression test added.

## Pass 2 — 4 holes sealed

7. **`_publish_to_player` blocked + editor callback `caller_id` validated** — Critical: attacker could forge an `editor` event with `caller_id` set to a wizard's pk, causing the callback to execute as wizard. Two-layer fix.
8. **`context.caller_stack` now returns a copy** — returned the live list; appending forged caller frames poisoned the stack across the worker process.
9. **`invoke()` wizard check for `periodic=True`/`cron=`** — non-wizards could flood the Celery beat schedule with unlimited `PeriodicTask` rows.
10. **`safe_builtins` copy on every call** — module-level singleton was mutated in place; a brief window existed where the real `getattr` was visible.

## Pass 3 — 4 holes sealed

11. **`_Context` made a data descriptor** — Critical: persistent cross-request privilege escalation. `setattr(context, "caller", wizard)` shadowed the contextvar-backed descriptor, poisoning `context.caller.is_wizard()` for all subsequent tasks in the Celery worker.
12. **`string` module removed from `ALLOWED_MODULES`** — `string.Formatter.get_field()` called real `getattr` internally, allowing unrestricted dunder access.
13. **`invoke()` execute permission check added** — `invoke(verb=some_verb)` dispatched without checking `execute` permission, allowing read-access holders to enqueue any verb.
14. **`_write_.__setitem__` now blocks underscore keys** — was checking `__setattr__` but not `__setitem__`.

## Pass 4 — 4 holes sealed

15. **`moo.core` submodules blocked via `BLOCKED_IMPORTS`** — Critical: `from moo.core import models` gave full ORM (`Object.objects.all()`, `User.objects.values("password")`, `Verb.objects.update(code=...)`).
16. **`_getitem_` underscore key guard added (read side)** — `_write_.__setitem__` blocked writes; `_getitem_` was a bare lambda with no check.
17. **Dead `"date"` entry removed from `ALLOWED_MODULES`** — no Python stdlib module named `date` exists; future third-party packages would become auto-accessible.
18. **`time.sleep()` / ReDoS documented as mitigated** — bounded by Celery task time limits; no code change needed.

## Pass 5 — 4 holes sealed + 1 known gap documented

19. **`str.format()` / `str.format_map()` blocked on string instances** — Critical: Python's C-level format engine resolved attribute chains via real `getattr`, bypassing all sandbox guards. `'{0.__class__}'.format(obj)` exposed dunder attributes on any object.
20. **`Verb.save()` permission check added** — verb code could get a verb via read access, set `verb.code = "malicious"`, and call `.save()` without a write check.
21. **`Property.save()` permission check added** — same pattern via `obj.properties.filter(name='x').first().save()`.
22. **`Object.delete()` permission check added** — any verb code holding an object reference could delete it unconditionally.

Known gap: `dict.update()` + `dict.get()` bypass (see known-gaps.md).

## Pass 6 — 4 holes sealed

23. **`QuerySet.model` / `.query` / `.db` blocked** — `obj.parents.all().model.objects.all()` gave full unauthenticated ORM access.
24. **`Property.value` readable without permission blocked** — `obj.properties.filter(name='x').first().value` bypassed the permission-checked `get_property()` path.
25. **`Verb.__call__()` execute permission check added** — direct `verb_obj(...)` call bypassed the `can_caller("execute")` check in `Object.invoke_verb()`.
26. **`obj.acl` enumerable without grant permission blocked** — reading the full ACL of any object revealed permission assignments.

## Pass 7 — 6 holes sealed

27. **`moo.sdk.ContextManager` accessible via module attribute blocked** — `import moo.sdk as sdk; sdk.ContextManager` bypassed `BLOCKED_IMPORTS`; fixed by `_ContextManager` alias + `ModuleType`+`BLOCKED_IMPORTS` attribute guard.
28. **`import moo.sdk` → `moo.core.models` attribute traversal blocked** — bare `import moo.sdk` bound the `moo` package; `moo.core.models.Object` passed through all guards. `ModuleType` guard added.
29. **QuerySet bulk mutations blocked** — `.update()`, `.delete()`, `.bulk_update()`, `.bulk_create()` issue SQL directly, bypassing model permission guards.
30. **`QuerySet.values()` / `values_list()` blocked** — returned plain dicts instead of `Property` instances, bypassing the `Property.value` guard.
31. **`RelatedManager.create()` blocked + `Verb.save()`/`Property.save()` extended to creates** — bypassed `add_verb()` / `set_property()` permission checks; model saves now check `can_caller("write")` for creates too.
32. **ManyToMany parent manipulation blocked + `add_parent()`/`add_alias()` helpers added** — `obj.parents.add()`, `.remove()`, `.clear()`, `.set()` issue SQL directly, bypassing `Object.save()` ACL checks.

## Pass 8 — 4 holes sealed

33. **`VerbName.save()` permission check added** — renaming a verb name without write access could silently redirect dispatch.
34. **`VerbName.delete()` permission check added** — deleting a verb name broke `invoke_verb` dispatch without any permission check.
35. **`Alias.delete()` permission check added** — `Alias.save()` was already guarded; `Alias.delete()` was not.
36. **`Verb.reload()` permission check added** — triggered a git repo fetch overwriting verb code without write permission.

## Pass 9 — 3 holes sealed (1 previously undocumented)

37. **`Verb.invoked_object` / `Verb.invoked_name` renamed to `_invoked_object` / `_invoked_name`** — writable from verb code via `get_verb()`; could spoof `this` in dispatch or redirect `passthrough()` to a different verb.
38–39. (See git history for pass 9 details.)

## Pass 10 — 3 holes sealed

40. **`Access.save()` permission check added** — an attacker with `grant` on their own object could reassign `access.object` to a wizard-protected object and inject an ACL entry.
41. **`Access.delete()` permission check added** — same acquisition path; could delete ACL entries on objects they had no grant over.
42. **`Repository.save()` / `Repository.delete()` wizard guard added** — non-wizard could change the `repo.url` to redirect future `verb.reload()` fetches to an attacker-controlled URL.

## Pass 11 — 1 hole sealed + 1 clarification

43. **`set_protected_attribute` bypassed ACL for Object writes** — Critical: `_write_(obj).__setattr__('name', value)` placed the value directly into `obj.__dict__`, bypassing `can_caller("write")` and shadowing DB-backed MOO properties in-memory for the Celery task. Now calls `obj.can_caller("write", obj)` for `AccessibleMixin` instances.

Clarification: `_apply_` is still generated by RestrictedPython in Python 3 for `func(*args)` calls; it is not a dead artifact.

## Pass 12 — 2 holes sealed

44. **`Verb.delete()` permission check added** — `Verb.save()` had a write guard but `Verb.delete()` did not.
45. **`Property.delete()` permission check added** — same oversight as `Verb.delete()`.

## Pass 13 — 1 hole sealed

46. **`original_owner` / `original_location` renamed to `_original_owner` / `_original_location`** — writable tracking fields allowed bypassing the `entrust` and `move` permission checks in `Object.save()` by pre-injecting the expected original value.

## Pass 14 — 0 holes + 8 confirmed-safe tests

No new holes. Systematic investigation confirmed: `setattr`/`delattr` builtins are safe (`guarded_setattr`/`guarded_delattr` from `safe_builtins`); `callable()`, `isinstance()`, `issubclass()` are safe; exception `__traceback__`/`__context__`/`__cause__` blocked by underscore guard; `select_related()`/`prefetch_related()` in `_QUERYSET_ALLOWED` open no new surface; `id()`, class definitions, `__build_class__` are harmless.

## Pass 15 — 3 holes sealed

47. **`getattr(gen, 'gi_frame')` frame-walk escape blocked** — Critical: `safe_getattr` never imported `INSPECT_ATTRIBUTES`, so the `getattr()` builtin path was unguarded. Full attack chain: `getattr(gen, 'gi_frame')` → `f_back` → `f_builtins` → `dict.get('__import__')` → `os.system('id')`. Both `safe_getattr` and `get_protected_attribute` now check `INSPECT_ATTRIBUTES`.
48. **`str.format` as class method blocked** — `str.format("{0.__class__}", obj)` bypassed the instance check (`isinstance(obj, str)` is `False` for the `str` type). Guard extended to `isinstance(obj, type) and issubclass(obj, str)`.
49. **`moo.sdk.contextmanager` and `moo.sdk.log` blocked via `BLOCKED_IMPORTS`** — both were non-underscore names in `sdk.py` not covered by the existing block; `log.info(msg)` allowed log injection.

## Pass 16 — 1 hole + 24 confirmed-safe tests

50. **`safe_hasattr` now checks `INSPECT_ATTRIBUTES`** — `hasattr(gen, 'gi_frame')` returned `True` even though `getattr` was blocked; boolean leak confirmed the frame attribute was accessible for reconnaissance.

Confirmed safe across 24 tests: PeriodicTask task registry gating; `django_celery_beat` not importable; wizard ORM read-only access accepted; `passthrough` cannot forge `this`; `invoke()` kwargs security fields overwritten from authenticated context; `AttributeError.obj` discloses nothing new; `re`/`hashlib`/`datetime`/`time` return types are safe; `sorted`/`enumerate`/`list`/`set` are safe; `context.writer` targets only the current player; `context.task_id` is a string; `context.parser` exposes only command-parsing info.

## Pass 17 — 0 holes + 14 confirmed-safe tests (new module addition)

**Date:** 2026-03-19
**Focus:** `random` module addition to `ALLOWED_MODULES`

No holes found. The `random` module was systematically evaluated across all attack categories before being added to `ALLOWED_MODULES`.

**Attack surface analysis:**
- **Dunder/MRO access** — Module, class, and instance dunder attributes blocked by existing underscore guard. Tested `__package__`, `__bases__`, `__class__` via `getattr()`.
- **Frame/inspection** — Random objects are not generators/coroutines; no `gi_frame`, `cr_frame`, or `f_back` attributes exist. `INSPECT_ATTRIBUTES` guard provides defense-in-depth.
- **Format string** — Random objects don't have `.format()` or `.format_map()` methods. Only strings trigger the format guard (pass 5/15).
- **Module traversal** — No submodules exposed. All exports are classes (`Random`, `SystemRandom`), functions (`randint`, `choice`), or numeric constants (`BPF`, `TWOPI`). `ModuleType` guard (pass 7) would block any future submodule additions.
- **ORM/Manager access** — Return types are `float`, `int`, `tuple`. No `QuerySet`, `Manager`, or model instances. `getstate()` returns a plain tuple `(VERSION, tuple_of_ints, None)`.
- **State manipulation** — `seed()` and `setstate()` manipulate module-level RNG state, but Celery execution model isolates each verb invocation in a task. State changes only affect the current task execution; no cross-task or persistent pollution possible.

**Tests added:** 14 new tests in `moo/core/tests/test_security_random.py` covering basic functionality, dunder blocks, frame checks, getstate safety, format method absence, module attributes, SystemRandom, state isolation, constants, and integration with existing guards.

**Changes:** Added `"random"` to `ALLOWED_MODULES` in `moo/settings/base.py:47`.

**Lessons learned:**
- RestrictedPython blocks dunder syntax (`obj.__class__`) at compile time, so security tests must use `getattr(obj, '__attr__')` instead or face `TypeError: exec() arg 1 must be a string, bytes or code object`.
- `dir()` and `type()` were removed from `ALLOWED_BUILTINS` in pass 1, so tests cannot enumerate attributes or inspect types directly. Use architectural spot-checks instead (e.g., `isinstance(x, int)`, `callable(f)`).
- Module addition audits benefit from the six-category checklist (dunder/MRO, frame/inspection, format string, module traversal, ORM/Manager, state manipulation) to ensure comprehensive coverage.

---

## Pass 18 — 1 hole sealed + 1 capability added

**Date:** 2026-03-28
**Focus:** LambdaMOO feature gap review — property ownership entrust enforcement and `remove_parent()` helper

### Hole sealed

51. **`Property.save()` now enforces `entrust` for owner changes** — `Property.owner` was documented as requiring `entrust` permission, but the guard only checked `write`. A verb author with write access to an object could reach a `Property` instance via `obj.property_set.filter(...).first()`, set `prop.owner = attacker_obj`, and call `.save()` — transferring ownership without entrust. Fix: added `_original_owner_id` tracking via `from_db()` (same pattern as `Object._original_owner`); `save()` now calls `origin.can_caller("entrust", self)` when `owner_id` changes.

Note: `from_db()` guard uses `if "owner_id" in field_names` to handle deferred-field QuerySets (e.g., from `bulk_update(["owner", "inherit_owner"])`), which only load a subset of fields.

### Capability added

- **`Object.remove_parent(parent)`** — symmetric counterpart to `add_parent()`. `obj.parents.remove()` is blocked by `_QUERYSET_ALLOWED` (ManyToMany mutation methods absent from allowed set), so there was no path for verb authors to remove a parent. The `m2m_changed` signal fires `can_caller("transmute")` + `can_caller("derive")` for both `pre_add` and `pre_remove`, providing double coverage alongside the explicit `can_caller("write")` check in the method body.

### Tests added

6 new tests in `moo/core/tests/test_security_models.py`:
- `test_property_owner_change_requires_entrust` — non-owner writer cannot transfer property ownership
- `test_property_owner_change_allowed_with_entrust` — wizard can transfer property ownership
- `test_property_value_change_does_not_require_entrust` — value-only change still only needs write (regression)
- `test_remove_parent_works` — wizard removes a parent; parent chain updated
- `test_remove_parent_requires_write` — read-only caller cannot remove a parent
- `test_add_parent_regression` — `add_parent()` unaffected

**Total:** 18 passes, 51 holes sealed, 781 tests (3 skipped).

---

## Known Gaps (Summary)

See [known-gaps.md](known-gaps.md) for full details.

1. **`dict.update()` bypass** — low risk; fix requires custom dict subclass
2. **`context.caller_stack` previous-caller reference** — information disclosure only
3. **`PeriodicTask` from `invoke(periodic=True)`** — wizard trust boundary, accepted
4. **Coroutine `cr_frame` via `getattr()`** — unconfirmed; highest priority for pass 17

---

## Future Areas (Pass 17+)

### ~~Priority 1: Coroutine `cr_frame` via `getattr()`~~ — Confirmed safe

RestrictedPython explicitly rejects `async def` at compile time:
`SyntaxError: ('Line 1: AsyncFunctionDef statements are not allowed.',)`.
Coroutine objects can never be created from verb code, so `cr_frame` is not reachable.
A regression test confirming `async def` raises `SyntaxError` should be added to `test_security_builtins.py`.

### Priority 2: New Django/Celery model additions

Any new model added to `moo/core/models/` must have `save()` and `delete()` permission guards following the pattern in `verb.py`, `property.py`, `object.py`, and `acl.py`. Check both methods — `delete()` has been missed multiple times.

### Priority 3: `WIZARD_ALLOWED_MODULES` surface creep

If new submodules are added to `WIZARD_ALLOWED_MODULES`, audit what names they export and whether any expose mutation paths not covered by `_QUERYSET_ALLOWED`. The `ModuleType` guard only checks the module's `__name__`; it does not recurse into the module's attribute namespace.

### Priority 4: `ALLOWED_BUILTINS` additions

Before adding any name to `ALLOWED_BUILTINS`, check whether its return type exposes non-underscore attributes that reach Django ORM instances or callable chains outside the sandbox.

### Completion criteria

Each item should result in either:
1. A passing test with a docstring explaining why the vector is safe, or
2. A passing test demonstrating the fix for a real hole.

Update this file with a new pass section when a batch is completed.
