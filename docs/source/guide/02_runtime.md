# The DjangoMOO Runtime

Like LambdaMOO, only certain kinds of data can appear in a DjangoMOO database and those are the objects MOO programs ("Verbs") can manipulate. Besides the typical set of Python primitives, the other types of values include :class:`.Object`, :class:`.Property` and :class:`.Verb`. Note the slight overlap between the built-in python class :class:`.object` and our ORM model :class:`.Object`

## Python Value Types and the restricted environment

Technically, a Verb can use any kind of Python value, but since all MOO code is run in a restricted Python environment, there are a number of limitations to consider:

* the `print()` built-in function sends output to the current player
* access to attributes beginning with underscores is disabled
* in-place variable modification is disabled
* only the builtins in `ALLOWED_BUILTINS` are available
* only the modules in `ALLOWED_IMPORTS` may be imported
* total runtime cannot exceed `CELERY_TASK_TIME_LIMIT` (default 3 seconds)
  * if a verb calls another verb as a method, the total runtime cannot exceed `CELERY_TASK_TIME_LIMIT`
* a verb can use `return` at any time

There's no equivalent concept to the LambdaMOO object notation, the only way to fetch object references is via the Python API:



```{eval-rst}
.. autofunction:: moo.core.lookup()
```
