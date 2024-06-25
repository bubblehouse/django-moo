# MOO Permissions

At this point, the LambdMOO Programmer's guide goes into details about object permissions, which is one of the areas that has been improved in DjangoMOO. Let's dive into the permissions structure as defined in DjangoMOO.

First, instead of the UNIX-like `R/W/X` bits on each object, DjangoMOO defines a customizable list of permission names in `DEFAULT_PERMISSIONS`, which defaults to this list:

* `anything` - a special permission that acts as a wildcard
* `read` - can read the essential attributes of an object, verb or property
* `write` - can modify the essential attributes of an object, verb or property
* `entrust` - can change the owner of an object
* `grant` - can set permissions on an object
* `execute` - can call a verb on an object
* `move` - can move an object
* `transmute` - can change the parents of an object
* `derive` - can change the children of an object
* `develop` - can modify the verbs of an object

The `read` bit controls whether or not the subject can obtain a list of the properties or verbs in the object. Symmetrically, the `write` bit controls whether or not the subject can add or delete properties on this object. The `grant` permission for this object is only granted to wizards or the owner of the object.

The `transmute` bit specifies whether or not the subject can create new objects with this one as the parent, while the parent needs a corresponding `derive` bit that allows new children to be added. The `derive` and `transmute` bit can only be set by a wizard or by the owner of the object.

Whenever a new object is created, DjangoMOO invokes the `set_default_permission(new_obj)` verb on the "System Object", the Object with `pk=1`. The default version of this verb sets the initial permissions for the new object:

    from moo.core import api

    obj = api.args[0]
    obj.allow('wizards', 'anything')
    obj.allow('owners', 'anything')
    obj.allow('everyone', 'read')

    if obj.kind == 'verb':
        obj.allow('everyone', 'execute')
    else:
        obj.allow('everyone', 'read')

You can also see here the 3 existing object groups the permission structure is currently aware of: `owners`, `wizards`, and `everyone`.

Another major change should be discussed here as well: in DjangoMOO, verbs run with the permission of the _caller_, not the original author of the verb. The permissions layer is what should protect all access, not the rights of the running application.

We'll get into more detail on verbs in a later section.
