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

## Checking Permissions in Code

In verbs and other Python code, always check permissions before allowing operations. The `can_caller()` method is an essential tool:

```python
from moo.core import context

obj = context.player.location
if not obj.can_caller("write"):
    context.writer("Permission denied.")
    return False

# Safe to modify the object
obj.set_property("description", "A new description")
return True
```

The `can_caller()` method checks if the current task's caller has the specified permission on the object. It returns `True` if the permission is granted, `False` otherwise.

### Common Permission Checks

```python
# Check if caller can read properties
if obj.can_caller("read"):
    props = obj.get_property("description")

# Check if caller can execute verbs
if obj.can_caller("execute"):
    result = obj.invoke_verb("my_verb")

# Check if caller can move the object
if obj.can_caller("move"):
    obj.location = new_location
    obj.save()

# Check if caller can change ownership
if obj.can_caller("entrust"):
    obj.owner = new_owner
    obj.save()
```

## Setting Permissions Programmatically

Whenever a new object is created, DjangoMOO invokes the `set_default_permission(new_obj)` verb on the "System Object", the Object with `pk=1`. The default version of this verb sets the initial permissions for the new object:

```python
from moo.core import context

obj = context.args[0]
obj.allow('wizards', 'anything')
obj.allow('owners', 'anything')
obj.allow('everyone', 'read')

if obj.kind == 'verb':
    obj.allow('everyone', 'execute')
else:
    obj.allow('everyone', 'read')
```

The `allow()` method grants a permission to a recipient:

```python
# Grant write permission to wizards
obj.allow('wizards', 'write')

# Grant read permission to everyone
obj.allow('everyone', 'read')

# Grant multiple permissions at once (via the owners)
obj.allow('owners', 'anything')  # 'anything' grants all permissions
```

You can also use the `deny()` method to explicitly revoke a permission:

```python
# Remove execute permission from everyone
obj.deny('everyone', 'execute')
```

## Permission Groups

The 3 existing object groups the permission structure is currently aware of are:

- `owners` - The owner of the object (typically set via the `owner` field)
- `wizards` - Special administrative users (typically marked with `wizard=True`)
- `everyone` - All other users

## Best Practices

1. **Always check permissions**: Never assume a caller has permission for an operation
2. **Fail safely**: Return meaningful error messages when permission is denied
3. **Use permission groups**: Leverage `owners`, `wizards`, and `everyone` rather than creating individual ACLs
4. **Grant minimal permissions**: Only grant permissions that are absolutely necessary
5. **Document permission requirements**: Make it clear in verb/property documentation what permissions are required
