# Objects in the DjangoMOO Database

This is another good opportunity to quote Pavel Curtis:

> Objects are, in a sense, the whole point of the MOO programming language. They are used to represent objects in the virtual reality, like people, rooms, exits, and other concrete things. Because of this, MOO makes a bigger deal out of creating objects than it does for other kinds of value, like integers.
>
> Numbers always exist, in a sense; you have only to write them down in order to operate on them. With objects, it is different. The object with number '#958' does not exist just because you write down its number. An explicit operation, the `create()` function described later, is required to bring an object into existence. Symmetrically, once created, objects continue to exist until they are explicitly destroyed by the `recycle()` function (also described later).
>
> The identifying number associated with an object is unique to that object. It was assigned when the object was created and will never be reused, even if the object is destroyed. Thus, if we create an object and it is assigned the number `#1076`, the next object to be created will be assigned `#1077`, even if `#1076` is destroyed in the meantime.

Objects in DjangoMOO are all custom subclasses of the Django Model class, so the "identifying number" is just the primary key of the object. Also, unlike LambdaMOO objects, there's a `save()` function that needs to be called when a change is made to the intrinsic properties of an object.

## Fundamental Object Attributes

There are several fundamental attributes to every object, defined by `moo.core.models.Object`:

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Object.pk

    The unique identifying number of this Object

.. autoattribute:: Object.name
   :no-index:
.. autoattribute:: Object.unique_name
   :no-index:
.. autoattribute:: Object.obvious
   :no-index:
.. autoattribute:: Object.owner
   :no-index:
.. autoattribute:: Object.parents
   :no-index:
.. autoattribute:: Object.location
   :no-index:
.. autoattribute:: Object.aliases

    :class:`Alias` instances can be created to give additional names for an instance.

.. autoattribute:: Object.contents

    This is the :class:`ReverseManyToOneDescriptor` of the `location` field above

.. autoattribute:: Object.children

    This is the :class:`ReverseManyToOneDescriptor` of the `parent` field above

.. autoattribute:: Object.placement_prep
   :no-index:
.. autoattribute:: Object.placement_target
   :no-index:
```

## Placement

Objects can be placed in a spatial relationship to another object in the same room.
Placement is stored as two fields on the object: `placement_prep` (a preposition string
like `"on"` or `"under"`) and `placement_target` (the object it is placed relative to).

The supported prepositions are defined by `PLACEMENT_PREPS` in `settings.py`:

```
on, under, behind, before, beside, over
```

Of these, `under` and `behind` are *hidden* placements (defined by `HIDDEN_PLACEMENT_PREPS`):
objects placed with those prepositions are invisible in the room contents listing and
unfindable by name through the parser. They can only be revealed by `look under <target>`
or `look behind <target>`.

The remaining prepositions (`on`, `before`, `beside`, `over`) are *visible* placements.
Obvious visible-placed objects appear grouped under their surface in the room contents:

```
On the desk: a coffee cup.
```

Placement is cleared automatically when an object is taken, dropped, or moved.
If the placement target is deleted, `SET_NULL` clears the `placement_target` FK and
the `placed_objects.update(placement_prep=None)` hook in `Object.delete()` clears the
dangling `placement_prep` on all placed children.

### Placement API

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. automethod:: Object.set_placement
.. automethod:: Object.clear_placement
.. automethod:: Object.is_placed
.. automethod:: Object.is_hidden_placement
.. autoattribute:: Object.placement

    Read-only property. Returns ``(prep, target)`` tuple, or ``None`` if not placed.
```

The `surface_types` property on the target object restricts which prepositions are
valid. If not set, any placement preposition is accepted:

```python
# In a verb or @eval:
desk = lookup("writing desk")
desk.set_property("surface_types", ["on", "beside"])
```

A bigger change to the DjangoMOO architecture starts to emerge here, around how permissions are specified.

* Player information is kept in a separate table, and `Player.avatar` is set to the Object the player controls.
* This Player instance also includes a reference to the Django `user` object and the `wizard` `Boolean` field.

> The parent/child hierarchy is used for classifying objects into general classes and then sharing behavior among all members of that class. For example, the LambdaCore database contains an object representing a sort of "generic" room. All other rooms are descendants (i.e., children or children's children, or ...) of that one. The generic room defines those pieces of behavior that are common to all rooms; other rooms specialize that behavior for their own purposes. The notion of classes and specialization is the very essence of what is meant by object-oriented programming.

The main change to this mechanism in DjangoMOO is support for multiple inheritance, i.e., objects can now have multiple parents.
