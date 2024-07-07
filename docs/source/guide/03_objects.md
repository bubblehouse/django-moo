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
.. autoattribute:: Object.unique_name
.. autoattribute:: Object.obvious
.. autoattribute:: Object.owner
.. autoattribute:: Object.parents
.. autoattribute:: Object.location
.. autoattribute:: Object.aliases
    :class:`Alias` instances can be created to give additional names for an instance.
.. autoattribute:: Object.contents
    This is the :class:`ReverseManyToOneDescriptor` of the `location` field above
.. autoattribute:: Object.children
    This is the :class:`ReverseManyToOneDescriptor` of the `parent` field above
```

A bigger change to the DjangoMOO architecture starts to emerge here, around how permissions are specified.
* Player information is kept in a separate table, and `Player.avatar` is set to the player Object as needed.
* This Player instance also includes a reference to the Django `user` object and the `wizard` `Boolean` field.

> The parent/child hierarchy is used for classifying objects into general classes and then sharing behavior among all members of that class. For example, the LambdaCore database contains an object representing a sort of "generic" room. All other rooms are descendants (i.e., children or children's children, or ...) of that one. The generic room defines those pieces of behavior that are common to all rooms; other rooms specialize that behavior for their own purposes. The notion of classes and specialization is the very essence of what is meant by object-oriented programming.

The main change to this mechanism in DjangoMOO is support for multiple inheritance, i.e., objects can now have multiple parents.
