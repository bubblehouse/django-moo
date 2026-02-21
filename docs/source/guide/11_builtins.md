# Built-in Functions
```{eval-rst}
.. py:currentmodule:: moo.core
.. autofunction:: moo.core.lookup()
.. autofunction:: moo.core.create()
.. autofunction:: moo.core.write()
.. autofunction:: moo.core.invoke()
```

## Object Attributes
```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Object.name
.. autoattribute:: Object.unique_name
.. autoattribute:: Object.obvious
.. autoattribute:: Object.owner
.. autoattribute:: Object.parents
.. autoattribute:: Object.location
```

## Object Methods
```{eval-rst}
.. py:currentmodule:: moo.core.models
.. automethod:: Object.find()
.. automethod:: Object.get_ancestors()
.. automethod:: Object.get_descendents()
.. automethod:: Object.add_verb()
.. automethod:: Object.invoke_verb()
.. automethod:: Object.get_verb()
.. automethod:: Object.has_verb()
.. automethod:: Object.set_property()
.. automethod:: Object.get_property()
.. automethod:: Object.is_allowed()
.. automethod:: Object.is_player()
.. automethod:: Object.owns()
```

## Property Attributes
```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Property.name
.. autoattribute:: Property.value
.. autoattribute:: Property.type
.. autoattribute:: Property.owner
.. autoattribute:: Property.origin
.. autoattribute:: Property.inherit_owner
```

## Verb Attributes
```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Verb.code
.. autoattribute:: Verb.repo
.. autoattribute:: Verb.filename
.. autoattribute:: Verb.ref
.. autoattribute:: Verb.owner
.. autoattribute:: Verb.origin
.. autoattribute:: Verb.ability
.. autoattribute:: Verb.method
```
