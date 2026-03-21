# How to Work with Permissions

For a complete list of available permission names and groups, see {doc}`../reference/permissions`.

## Checking Permissions in Code

To improve the player experience, it's helpful to check permissions before allowing operations. The `can_caller()` method is one:

```python
from moo.sdk import context

obj = context.player.location
if not obj.can_caller("write"):
    context.writer("Permission denied.")
    return False

# Safe to modify the object
obj.set_property("description", "A new description")
return True
```

The `can_caller()` method checks if the current task's caller has the specified permission on the object. It returns `True` if the permission is granted, `False` otherwise.

The `caller` is usually the correct object to check for permissions, but very rarely you actually want to know if the current `player` is able to do something. In those cases, you can emulate `can_caller()` with:

```python
from moo.sdk import context
# can the player object edit the room object?
context.player.is_allowed("write", context.player.location)
```

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
from moo.sdk import context, set_task_perms

obj = args[0]
with set_task_perms(context.player):
    obj.allow("wizards", "anything")
    obj.allow("owners", "anything")

    if obj.kind == "verb":
        obj.allow("everyone", "execute")
    elif obj.kind == "property":
        obj.allow("everyone", "read")
    elif obj.kind == "object":
        obj.allow("everyone", "read")
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

## Best Practices

1. Always check permissions: every object operation is ruled by the permission system, so it's important to write verbs that handle failure gracefully.
2. Fail helpfully: return meaningful error messages when permission is denied.
3. Use permission groups: for common code, leverage `owners`, `wizards`, and `everyone` rather than creating individual ACLs.
4. Grant minimal permissions: only grant permissions that are absolutely necessary; complex ACLs can be difficult to debug.
5. Document permission requirements: make it clear in verb/property documentation what permissions are required.
