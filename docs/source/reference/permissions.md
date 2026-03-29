# MOO Permissions Reference

At this point, the LambdaMOO Programmer's guide goes into details about object permissions, which is one of the areas that has been improved in DjangoMOO. Let's dive into the permissions structure as defined in DjangoMOO.

Instead of the UNIX-like `R/W/X` bits on each object, DjangoMOO defines a customizable list of permission names in `DEFAULT_PERMISSIONS`, which defaults to this list:

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

## Permission Groups

The 3 existing object groups the permission structure is currently aware of are:

* `owners` - The owner of the object (typically set via the `owner` field)
* `wizards` - Special administrative users (typically marked with `wizard=True`)
* `everyone` - All other users

For code patterns on checking and setting permissions, see {doc}`../how-to/permissions`.
