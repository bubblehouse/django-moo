# Permissions Reference

DjangoMOO replaces LambdaMOO's UNIX-style `R/W/X` bits with a
customisable list of named permissions. The full list is declared in
`settings.DEFAULT_PERMISSIONS` and pre-created as `Permission` rows by
`bootstrap.initialize_dataset()`.

## Permission names

| Permission | Effect |
|------------|--------|
| `anything` | Wildcard — grants every other permission. |
| `read` | Read essential attributes (an object's contents and verb/property names; a property's value; a verb's source). |
| `write` | Modify essential attributes; add or delete properties on an object. |
| `execute` | Invoke a verb. |
| `move` | Change an object's `location` via `moveto()`. |
| `transmute` | Add this object as a child of another (gives this object a new parent). |
| `derive` | Add a new child to this object (parents need this on themselves before children can `transmute` to them). |
| `entrust` | Change an object's, property's, or verb's `owner`. |
| `grant` | Set or modify ACL rows on an object. Implicitly held by wizards and the object's owner. |

`grant`, `entrust`, `transmute`, and `derive` only ever apply to
wizards or the owner of the object — they're escalated permissions
that protect the permission system itself.

### Granular permissions are independent of `write`

Each granular permission (`move`, `entrust`, `transmute`, `derive`)
is checked on its own. A caller granted `move` on an object can call
`obj.moveto(target)` without also holding `write` — and likewise for
`entrust` (change the owner), `transmute` (add a parent), and
`derive` (be added as a parent). `write` is only required when a
non-ACL field changes during the same save: `name`, `unique_name`,
`obvious`, `placement_*`, or `site`.

This lets you, for example, hand an automation account `move` rights
on a fleet of NPC objects so it can teleport them without giving it
permission to rename or reparent them.

## Permission groups

ACL rows match against three group names. Resolution checks the
caller's role and falls through:

| Group | Matches |
|-------|---------|
| `owners` | The object's `owner` field. |
| `wizards` | Players whose `Player.wizard` is `True`. |
| `everyone` | Anyone else who passes the earlier groups. |

A grant to `everyone` applies to all callers; `wizards` and `owners`
narrow the audience.

## Where each permission is enforced

Permissions fire automatically at the model layer. Verb code does not
need to check first; an `AccessError` propagates and the player sees a
clean error. (See {doc}`../how-to/permissions` for the just-attempt-it
pattern.)

| Operation | Permission | Object the check is against |
|-----------|------------|-----------------------------|
| `Object.delete()` | `write` | the object |
| `Object.set_property(name, value)` | `write` | the object |
| `Object.add_verb(...)` | `write` | the object |
| `Object.moveto(target)` | `move` | the moving object |
| `Object.parents.add(parent)` | `transmute` + `derive` | child needs `transmute`; parent needs `derive` |
| `Object.find(name)` | `read` | the object being searched |
| `Property.save()` (new row) | `write` | the origin object |
| `Property.save()` (update) | `write` (+ `entrust` if `owner` changes) | the property |
| `Property.delete()` | `write` | the property |
| `Verb.save()` (new row) | `write` | the origin object |
| `Verb.save()` (update) | `write` (+ `entrust` if `owner` changes) | the verb |
| `Verb.delete()` | `write` | the verb |
| `Verb.__call__()` | `execute` | the verb |
| Reading `obj.acl` from verb code | `grant` | the object |
| Reading `Property.value` directly | `read` | the property |

## Default permissions on new objects

When an Object, Verb, or Property is created,
`apply_default_permissions` (in `moo/core/utils.py`) inserts three ACL
rows automatically:

- `wizards` are allowed `anything`.
- `owners` are allowed `anything`.
- `everyone` is allowed `read` (objects, properties) or `execute`
  (verbs).

This runs natively rather than via a verb. Custom datasets can add
further grants in their bootstrap finalize script — see
{doc}`../how-to/permissions` for the canonical `derive` grant from
`default/999_finalize.py`.

## See also

- {doc}`../how-to/permissions` — caller-vs-player, `set_task_perms`,
  `is_wizard`/`owns` patterns, and granting in bootstrap vs. verb
  code.
- {doc}`sandbox` — the model-layer enforcement details, attribute
  guards, and the `Property.value` read check.
