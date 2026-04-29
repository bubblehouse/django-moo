# Properties on Objects

Properties are typed key-value rows attached to an Object. Children
inherit every property defined on their parents — owners follow the
child by default, or stay pinned to the parent if `inherit_owner=True`.

For function reference (signatures of `set_property`, `get_property`,
etc.) see {doc}`builtins`. For the lookup architecture and caching
behaviour, see {doc}`caching`.

## Reading a property

The canonical pattern is `try/except`:

```python
from moo.sdk import NoSuchPropertyError

try:
    description = obj.get_property("description")
except NoSuchPropertyError:
    description = "You see nothing special."
```

`get_property()` walks the inheritance chain and deserialises the
value. It honours the three-tier cache (per-session dict → Redis →
database with `AncestorCache` join), so repeat reads inside a single
command are free.

**Don't pair `has_property()` with `get_property()`.** That makes two
queries for the same data. The `try/except` form does one.

`obj.<name>` via `__getattr__` also resolves to a property if no verb
matches first, but the verb miss is one extra database hit. Use
`get_property("name")` when you know it's a property.

To get the underlying `Property` ORM instance instead of the
deserialised value (e.g. to read its owner or permissions), pass
`original=True`:

```python
prop = obj.get_property("description", original=True)
prop.owner       # Player who owns this property row
prop.inherit_owner
```

## Writing a property

```python
obj.set_property("description", "A dark, cold room.")
```

`set_property` saves its own row — you do not need to call
`obj.save()` afterwards. To create a property where children should
keep the parent's ownership rather than rebasing to each child's
owner, pass `inherit_owner=True`:

```python
obj.set_property("ps", "they", inherit_owner=True)
```

See "Inheritance" below for what that flag actually changes.

## Permissions

Adding a new property to an object requires `write` permission on the
**object**. Updating an existing property requires `write` on the
**property** itself. Changing a property's owner requires `entrust`.
Deleting a property requires `write`.

Like every model-layer permission check, these fire automatically in
`Property.save()` and `Property.delete()` — verb code does not need
to check first. If the caller lacks the permission, `AccessError`
propagates and the player sees a clean error message. See
{doc}`../how-to/permissions`.

The named permissions a property recognises:

| Permission | Effect |
|------------|--------|
| `read` | Read the property value |
| `write` | Modify the property value |
| `entrust` | Change the owner of the property |
| `grant` | Set permissions on the property |
| `anything` | Wildcard — all of the above |

## Property attributes

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Property.pk

    The unique identifying number of this Property.

.. autoattribute:: Property.name
   :no-index:
.. autoattribute:: Property.value
   :no-index:
.. autoattribute:: Property.type
   :no-index:
.. autoattribute:: Property.owner
   :no-index:
.. autoattribute:: Property.origin
   :no-index:
.. autoattribute:: Property.inherit_owner
   :no-index:
```

## Inheritance and `inherit_owner`

When a child object reads a property defined on a parent, the child
gets its own row with the parent's value copied in. By default, the
child's owner becomes the *property's* owner on the child — so any
verb running as the child's owner can modify the property.

`inherit_owner=True` reverses that: the child's row keeps the
parent's owner. This matters when a parent verb (running as the
parent's owner) needs to mutate the property on every descendant.
Without `inherit_owner=True`, the verb loses write access on every
descendant whose owner is a different player.

The classic example: a `Generic Player` defines pronoun properties
(`ps`, `po`, `pp`, ...) that the `gender_utils` verb (owned by
Wizard) updates when a player runs `@gender male`. With
`inherit_owner=True` on those properties, every player's pronoun
properties are still owned by Wizard, and the wizard verb can change
them. Without it, each player would own their own pronoun rows and
the wizard verb would hit `AccessError`.

```python
# In a bootstrap script:
player_class.set_property("ps", "they", inherit_owner=True)
```

For the LambdaMOO origin of this design (the `c` permission bit), see
the LambdaMOO Programmer's Manual.
