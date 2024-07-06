# Properties on Objects

Since we're using "stock" Django model instances inside our custom code, the initial implementation of custom object properties are distinct from the `getattr()`-accessible attributes described above, e.g.:

    from moo.core import api

    description = api.caller.location.properties.filter(name="description")
    print(description.value)

Future improvements to the `AccessibleObject` abstract class may allow for direct access.

> First, an object has a property corresponding to every property in its parent object. To use the jargon of object-oriented programming, this is a kind of inheritance. If some object has a property named `foo`, then so will all of its children and thus its children's children, and so on.
>
> Second, an object may have a new property defined only on itself and its descendants. For example, an object representing a rock might have properties indicating its weight, chemical composition, and/or pointiness, depending upon the uses to which the rock was to be put in the virtual reality.
>
> Every defined property (as opposed to those that are built-in) has an owner and a set of permissions for non-owners. The owner of the property can get and set the property's value and can change the non-owner permissions. Only a wizard can change the owner of a property.
>
> The initial owner of a property is the player who added it; this is usually, but not always, the player who owns the object to which the property was added. This is because properties can only be added by the object owner or a wizard, unless the object is publicly writable (i.e., its `w` property is 1), which is rare. Thus, the owner of an object may not necessarily be the owner of every (or even any) property on that object.

To add a new Property to an object, users must have the `write` permission on that object (owners and wizards get this by default). Properties support the following permissions for any given object or object group:

* `anything` - do anything with a property
* `read` - read the property value
* `write` - modify the property value
* `entrust` - can change the owner of a property
* `grant` - can set permissions on a property

Every property has the following attributes:

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Property.pk

    The unique identifying number of this Property

.. autoattribute:: Property.name
.. autoattribute:: Property.value
.. autoattribute:: Property.type
.. autoattribute:: Property.owner
.. autoattribute:: Property.origin
.. autoattribute:: Property.inherited
```

#### Property Inheritance

This section is complicated enough to call out in a separate heading. In LambdaMOO, there was a third permission bit `c` ... that wasn't really a permission bit.

> Recall that every object has all of the properties that its parent does and perhaps some more. Ordinarily, when a child object inherits a property from its parent, the owner of the child becomes the owner of that property. This is because the `c` permission bit is "on" by default. If the `c` bit is not on, then the inherited property has the same owner in the child as it does in the parent.
>
> As an example of where this can be useful, the LambdaCore database ensures that every player has a `password` property containing the encrypted version of the player's connection password. For security reasons, we don't want other players to be able to see even the encrypted version of the password, so we turn off the `r` permission bit. To ensure that the password is only set in a consistent way (i.e., to the encrypted version of a player's password), we don't want to let anyone but a wizard change the property. Thus, in the parent object for all players, we made a wizard the owner of the password property and set the permissions to the empty string, "". That is, non-owners cannot read or write the property and, because the `c` bit is not set, the wizard who owns the property on the parent class also owns it on all of the descendants of that class.

... we don't actually have this specific problem because passwords are kept externally from the game code ...

> Another, perhaps more down-to-earth example arose when a character named Ford started building objects he called "radios" and another character, yduJ, wanted to own one. Ford kindly made the generic radio object fertile, allowing yduJ to create a child object of it, her own radio. Radios had a property called `channel` that identified something corresponding to the frequency to which the radio was tuned. Ford had written nice programs on radios (verbs, discussed below) for turning the channel selector on the front of the radio, which would make a corresponding change in the value of the `channel` property. However, whenever anyone tried to turn the channel selector on yduJ's radio, they got a permissions error. The problem concerned the ownership of the `channel` property.
>
> As I explain later, programs run with the permissions of their author. So, in this case, Ford's nice verb for setting the channel ran with his permissions. But, since the `channel` property in the generic radio had the `c` permission bit set, the `channel` property on yduJ's radio was owned by her. Ford didn't have permission to change it! The fix was simple. Ford changed the permissions on the `channel` property of the generic radio to be just `r`, without the `c` bit, and yduJ made a new radio. This time, when yduJ's radio inherited the `channel` property, yduJ did not inherit ownership of it; Ford remained the owner. Now the radio worked properly, because Ford's verb had permission to change the channel.
>

DjangoMOO properties support an `inherit` attribute that works the same way as LambdaMOO's `c` bit. When this attribute is set, children will inherit the property with the owner set to that of the child. Here's some pseudocode that creates a default room class that adds a default description to all its children, and ensures those children's owner can modify it:

    room = create('default room')
    room.set_property("description", "There's not much to see here.", inherited=True)

In our case, verbs run with the permission of the caller, but a similar issue would happen. To paraphrase the above, when **yduJ** ran one of **Ford's** verbs on a radio derived from his, they would run with **yduJ's** permissions, but the inherited properties would have been owned by **Ford**. By changing the ownership of the inherited property to belong to **yduJ**, the verb will run correctly.
