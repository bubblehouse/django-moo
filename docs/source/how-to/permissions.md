# How Permissions Work in Verbs

DjangoMOO's permission system is mostly invisible. Most verbs do not
check permissions — they attempt the operation, and if it isn't
allowed, an `AccessError` propagates out, the transaction rolls back,
and the player sees a clean red error line. Verb authors only reach
for explicit checks in a few specific situations, listed at the end of
this guide.

For the permission *names* (`read`, `write`, `execute`, etc.) and the
groups (`owners`, `wizards`, `everyone`), see {doc}`../reference/permissions`.

## The just-attempt-it model

Permissions are enforced at the model layer. Every save, delete,
property write, and verb execution funnels through a permission check
before touching the database. If the check fails, `AccessError`
(a subclass of Python's `PermissionError`) is raised with the form:

```
AccessError("<accessor> is not allowed to '<action>' on <subject>")
```

The task runner in `moo.core.tasks.parse_command` catches
`PermissionError` automatically and renders it to the player:

```
PermissionError: #5 (Wizard) is not allowed to 'write' on #176 (heavy wooden workbench)
```

That's the same UX as a `UserError` — bold red, single line, no
traceback for non-wizards. Because the runner catches it, **a verb
that just calls `obj.set_property(...)` and lets the call fail is
already doing the right thing.** No `try/except`, no preflight
`can_caller`, no manual error message.

This is why none of the default verbs (with the exception of role
checks discussed below) use `can_caller()` — the system handles it.

## Caller vs. player

Two `context` attributes track who's involved:

- `context.player` — the Object that originated the command. Stays
  pinned to the session initiator across nested verb calls.
- `context.caller` — the object whose verb code is currently
  executing. Changes as verbs invoke other verbs.

**Permissions are evaluated against `context.caller`, not
`context.player`.** That is the key. The effective permissions of
running code are the permissions of *the verb's owner*, not the
permissions of the player who typed the command.

This is why a non-wizard player can run `@create` even though
`@create` does things like setting up ACL rows: the verb is owned by
`Wizard` (every default verb is, because the bootstrap runs as
Wizard). When the verb body runs, `context.caller` is the verb's
owner — Wizard — and the operations inside succeed regardless of who
typed the command. The `$builder` class in the verb's `--on` line
controls *where the verb lives* (which objects can dispatch to it);
it has nothing to do with what the verb is allowed to do.

It's also why a verb owned by a regular player can't quietly mutate
wizard-owned objects when the wizard happens to invoke it: the
verb's caller is still the regular owner, and the model-layer check
fires.

## Overriding the caller with `set_task_perms`

Sometimes a wizard-owned verb needs to perform an action *as* the
player who triggered it. The classic case is creating an object that
should be owned by the player, not by the verb's wizard owner.
`set_task_perms(who)` is a context manager that swaps `context.caller`
for the duration of a block.

`default/verbs/builder/at_create.py` shows the pattern:

```python
from moo.sdk import context, create, set_task_perms

# Resolve parent up front so we can pass it to create() in one step.
parent = None
if context.parser.has_pobj_str("from"):
    with set_task_perms(context.player):
        parent = context.parser.get_pobj("from", lookup=True)

with set_task_perms(context.player):
    if parent is not None:
        new_obj = create(name, owner=context.player, location=location, parents=[parent])
    else:
        new_obj = create(name, owner=context.player, location=location)
```

`@create` is owned by Wizard, so the verb runs with wizard
permissions by default. But the new object should *belong* to the
player. Wrapping the `create()` call in
`with set_task_perms(context.player):` makes the database insert
execute as the player, so:

- The new object's owner is the player.
- The default-permission ACL rows for the new object are created
  under the player's authority.
- Any further model-layer checks during the call (parent lookup,
  location validation) are evaluated against the player's
  permissions, not the verb owner's.

`set_task_perms` raises `UserError` for non-wizards. Only wizard-
owned verbs can use it.

A second example is `default/verbs/programmer/at_eval.py`, which
evaluates user-supplied code with `set_task_perms(context.player)` so
the snippet runs with the player's permissions rather than the
wizard owner's — closing the obvious privilege-escalation hole.

## Role and ownership branching

A handful of verbs need to take *different actions* based on who's
running them — not because they need to guard a write, but because
the right behaviour differs for wizards vs. owners vs. everyone else.
Use `is_wizard()` and `owns()` for these. They check role and
ownership directly, not ACL bits.

`default/verbs/programmer/at_reload.py` uses both:

```python
target = context.parser.get_pobj("on", lookup=True)
verb = target.get_verb(target_verb_name)
if not context.player.is_wizard() and not context.player.owns(verb):
    print("Permission denied.")
    return
verb.reload()
```

This isn't a redundant ACL guard — `verb.reload()` already enforces
its own permissions at the model layer. The check exists so that
non-owners get a clear "Permission denied" message *before* the
filesystem read happens, rather than an `AccessError` after.

The criterion for adding such a check: it changes what the verb
*does*, not just whether it errors. If the only effect of the check
is "raise instead of letting the model raise," delete it.

## When to use `can_caller`

`can_caller(perm)` answers "would this operation succeed if I tried
it?" without actually trying it. The legitimate uses are:

- **Conditional output.** An `examine` verb that shows an "edit this"
  hint only to people who could edit it.
- **Choosing between two safe paths** based on permission level.
- **Pre-screening a long-running operation** so the player doesn't
  wait for a job that's going to fail at the end.

It is not a guard for writes. Writing
`if not obj.can_caller("write"): return` ahead of `obj.save()` is
just duplicating the model-layer check that's about to fire anyway —
and the `AccessError` from `save()` already produces a better message
than a hand-rolled "Permission denied".

## Granting and revoking permissions

`obj.allow(group, perm)` and `obj.deny(group, perm)` add and remove
ACL rows. The legitimate use cases are bootstrap-time setup and admin
tools, not in-line verb code.

### From bootstrap code

Bootstrap scripts run outside the RestrictedPython sandbox, so they
can import Django ORM models directly and bulk-create ACL rows.
`default/999_finalize.py` grants the `derive` permission to every
player on every standard system class so that anyone can run
`@create "name" from $thing` without needing wizard privileges:

```python
# moo/bootstrap/default/999_finalize.py — bootstrap script, NOT verb code
from moo.core.models.acl import Access, Permission

derive_perm = Permission.objects.get(name="derive")
for _cls in [root, thing, rooms, exits, player, builders, programmers, ...]:
    Access.objects.get_or_create(
        object=_cls,
        permission=derive_perm,
        type="group",
        group="everyone",
        rule="allow",
    )
```

`get_or_create` makes the loop idempotent so `moo_init --sync` can
re-run it cleanly.

The `Permission` and `Access` ORM models used here are **not
importable from verb code** — `moo.core.models.acl` is outside
`ALLOWED_MODULES`. This pattern is reserved for bootstrap and
management commands.

### From verb code

In a verb, use the higher-level helpers on the object itself:

```python
obj.allow("everyone", "read")
obj.allow("wizards", "anything")
obj.deny("everyone", "execute")
```

`anything` is a wildcard that grants every permission at once.
These calls are subject to the usual permission checks — the caller
needs the `grant` permission on the target object, which by default
is held by wizards and the object's owner.

## Default permissions on new objects

When an Object, Verb, or Property is created, three ACL rows are
inserted automatically by `apply_default_permissions` in
`moo/core/utils.py`:

- `wizards` are allowed `anything`.
- `owners` are allowed `anything`.
- `everyone` is allowed `read` (for objects/properties) or `execute`
  (for verbs).

This runs natively, not via a verb, so verb authors never need to
think about it. (There is a `set_default_permissions` verb file in
`default/verbs/`, but it exists as documentation; the executable
path is the native function.)

## Where to read more

- {doc}`../reference/permissions` — permission names, the three
  groups, and what each permission gates.
- {doc}`../reference/sandbox` — the model-level enforcement: which
  saves/deletes/calls trigger permission checks and why.
- {doc}`../reference/runtime` — full `context.caller` /
  `context.player` reference.
