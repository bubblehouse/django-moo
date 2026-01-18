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
    write(obj, "A parrot squawks.")
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
    write(obj, f"A parrot squawks {value}.")
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

This works basically the same in DjangoMOO verb code because all verbs are built with RestrictedPython's `compile_restricted_function` feature, and run inside a Python function definition that looks like this:

```python
    def verb(this, passthrough, _, *args, **kwargs):
        """
        :param this: the Object where the current verb was found, often a child of the origin object
        :param passthrough: a function that calls the current function on the parent object, somewhat similar to super()
        :param _: a reference to the #1 or "system" object
        :param args: function arguments when run as a method, or an empty list
        :param kwargs: function arguments when run as a method, or an empty dict
        :return: Any
        """
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
