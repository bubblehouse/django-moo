### Calling Other Verbs

Like properties, the default Django ORM doesn't honor inheritance, so there's a few custom methods on Object instances to help out.

The simplest way to invoke another verb (as a method) from a running verb is with:

```python
obj.invoke_verb(name, *args, **kwargs)
```

or using the getattr override:

```python
obj.announce(*args, **kwargs)
```

This works for many convenience functions, but whatever time these functions use will count against the default
verb timeout of 3 seconds.

But if you're limited to 3 seconds in a Verb, how do you create longer tasks? The key is to compose your function
into multiple Verb calls, which you can invoke asynchronously using the `invoke()` function:

```{eval-rst}
.. py:currentmodule:: moo.core
.. autofunction:: invoke
```

Using `invoke()` let's create a bad example of a talking parrot:

```python
from moo.core import api, invoke
if api.parser is not None:
    invoke(api.parser.verb, delay=30, periodic=True)
    return
for obj in api.caller.location.filter(player__isnull=False):
    api.writer(obj, "A parrot squawks.")
```

Right now it's just repeating every thirty seconds, but we can make it slightly more intelligent
by handling our own repeating Verbs:

```python
from moo.core import api, invoke
if api.parser is not None:
    invoke(api.parser.verb, delay=30, value=0)
    return
value = kwargs['value'] + 1
for obj in api.caller.location.filter(player__isnull=False):
    api.writer(obj, f"A parrot squawks {value}.")
invoke(api.parser.verb, delay=30, value=value)
```

Let's say we didn't want to handle writing ourselves (we shouldn't) and wanted instead
to re-use the `say` Verb.

```python
from moo.core import api, invoke
if api.parser is not None:
    say = api.caller.get_verb('say', recurse=True)
    invoke(verb=api.parser.verb, callback=say, delay=30, value=0)
    return
value = kwargs['value'] + 1
return f"A parrot squawks {value}."
```

### Returning a Value from a Verb

> The MOO program in a verb is just a sequence of statements. Normally, when the verb is called, those statements are simply executed in order and then the integer 0 is returned as the value of the verb-call expression. Using the `return` statement, one can change this behavior. The `return` statement has one of the following two forms:
>
> `return`
>
> or
>
> `return _expression_`
>
> When it is executed, execution of the current verb is terminated immediately after evaluating the given expression, if any. The verb-call expression that started the execution of this verb then returns either the value of expression or the integer 0, if no expression was provided.

This works basically the same in DjangoMOO verb code because all verbs are compiled with RestrictedPython's `compile_restricted_function` feature. The game engine automatically wraps your verb code with a function that provides these parameters:

- `this`: The object where the current verb was found, often a child of the origin object
- `passthrough`: A function that calls the current verb on the parent object, somewhat similar to `super()`
- `_`: A reference to the #1 or "system" object
- `args`: Function arguments when run as a method, or an empty list
- `kwargs`: Keyword arguments when run as a method, or an empty dict

One key advantage of RestrictedPython is that `return` can be used from anywhere in the verb code, not just at the end of functions:

```python
#!moo verb check_object --on $room

from moo.core import api

# Early return for empty arguments
if not args:
    return "Syntax: check_object <object_name>"

# Find the object
obj_name = args[0]
found_objs = this.contents.filter(name=obj_name)

if not found_objs.exists():
    return f"I don't see '{obj_name}' here."

# Check permissions
obj = found_objs.first()
if not obj.can_caller("read"):
    return "You don't have permission to examine that."

# Return success information
return f"Object: {obj.name}\nDescription: {obj.get_property('description')}"
```

### Handling Verb Errors

DjangoMOO defines a number of custom exceptions:

```{eval-rst}
.. py:currentmodule:: moo.core.exceptions
.. autoclass:: UsageError
.. autoclass:: UserError
.. autoclass:: AccessError
.. autoclass:: AmbiguousObjectError
.. autoclass:: AmbiguousVerbError
.. autoclass:: ExecutionError
.. autoclass:: NoSuchPrepositionError
.. autoclass:: QuotaError
.. autoclass:: RecursiveError
```

## Best Practices for Verb Development

### 1. Always Check Permissions First

```python
from moo.core import api

if not this.can_caller("write"):
    return "Permission denied."
```

### 2. Validate Arguments Early

```python
if len(args) < 2:
    return "Usage: verb_name <arg1> <arg2>"
```

### 3. Use the API Context

```python
from moo.core import api

# api.caller is the effective caller (usually verb owner)
# api.player is the player executing the command
# api.writer sends output to the player
# api.parser contains parsed command info
```

### 4. Return Meaningful Messages

```python
# GOOD: Descriptive error messages
if not obj:
    return "That object doesn't exist."

# GOOD: Confirm success
return "Object created successfully."

# AVOID: Silent failures
return None
```

### 5. Keep Verbs Focused

Each verb should do one thing well. If you need complex logic:

```python
from moo.core import api, invoke

# Split into multiple async operations
invoke(verb=complex_verb, delay=0, context={...})
return "Operation started in background."
```

### 6. Use Database Queries Efficiently

```python
# GOOD: Use select_related for foreign keys
objs = Object.objects.select_related('owner', 'location')

# GOOD: Use prefetch_related for backward relations
objs = Object.objects.prefetch_related('properties', 'verbs')

# AVOID: N+1 queries
for obj in Object.objects.all():
    print(obj.owner.name)  # Query per object
```

### 7. Handle Errors Gracefully

```python
try:
    result = verb_operation()
    return result
except AttributeError:
    return "Invalid object reference."
except ValueError as e:
    return f"Invalid value: {str(e)}"
except Exception as e:
    return f"An error occurred: {str(e)}"
```
