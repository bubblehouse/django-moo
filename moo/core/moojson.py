"""
Encode/decode MOO JSON
"""

import json


def loads(j):
    from .models import Object, Property, Verb

    def to_entity(d):
        if len(d) != 1:
            return d
        key = list(d.keys())[0]
        if key[1] == "#":
            if key[0] == "o":
                return Object.objects.get(pk=int(key[2:]))
            elif key[0] == "v":
                return Verb.objects.get(pk=int(key[2:]))
            elif key[0] == "p":
                return Property.objects.get(pk=int(key[2:]))
        return d

    return json.loads(j, object_hook=to_entity)


def dumps(obj):
    from .models.object import Object, AccessibleObject
    from .models.property import Property, AccessibleProperty
    from .models.verb import Verb, AccessibleVerb

    def from_entity(o):
        if isinstance(o, (Object, AccessibleObject)):
            return {"o#%d" % o.pk: str(o)}
        elif isinstance(o, (Verb, AccessibleVerb)):
            return {"v#%d" % o.pk: str(o)}
        elif isinstance(o, (Property, AccessibleProperty)):
            return {"p#%d" % o.pk: str(o)}
        else:
            raise TypeError(
                "Unserializable object {} of type {}".format(obj, type(obj))
            )
    return json.dumps(obj, default=from_entity)
