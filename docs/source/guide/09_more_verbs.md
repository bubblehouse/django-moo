### Calling Other Verbs

Like properties, the default Django ORM doesn't honor inheritance, so there's a few custom methods on Object instances to help out.

The best way to invoke another verb (as a method) from a running verb is with:

    obj.invoke_verb(name, **args, **kwargs)

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

This works basically the same in DjangoMOO verb code because all verbs are built with RestrictedPython's `compile_restricted_function` feature, and run inside a Python function definition.

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
.. autoclass:: NoSuchObjectError
.. autoclass:: NoSuchPrepositionError
.. autoclass:: NoSuchPropertyError
.. autoclass:: NoSuchVerbError
.. autoclass:: QuotaError
.. autoclass:: RecursiveError
```
