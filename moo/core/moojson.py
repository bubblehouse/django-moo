"""
Encode/decode MOO JSON
"""

import json
from datetime import date, datetime, time


def loads(j):
    from .models.object import Object
    from .models.property import Property
    from .models.verb import Verb

    def to_entity(d):
        if len(d) != 1:
            return d
        key = list(d.keys())[0]
        if key == "dt#":
            return datetime.fromisoformat(d[key])
        if key == "d#":
            return date.fromisoformat(d[key])
        if key == "t#":
            return time.fromisoformat(d[key])
        if len(key) >= 2 and key[1] == "#":
            if key[0] == "o":
                return Object.objects.get(pk=int(key[2:]))
            elif key[0] == "v":
                return Verb.objects.get(pk=int(key[2:]))
            elif key[0] == "p":
                return Property.objects.get(pk=int(key[2:]))
        return d

    return json.loads(j, object_hook=to_entity)


def dumps(obj):
    from .models.object import Object
    from .models.property import Property
    from .models.verb import Verb

    def from_entity(o):
        if isinstance(o, datetime):
            return {"dt#": o.isoformat()}
        elif isinstance(o, date):
            return {"d#": o.isoformat()}
        elif isinstance(o, time):
            return {"t#": o.isoformat()}
        elif isinstance(o, Object):
            return {"o#%d" % o.pk: o.name}
        elif isinstance(o, Verb):
            return {"v#%d" % o.pk: o.name()}
        elif isinstance(o, Property):
            return {"p#%d" % o.pk: o.name}
        else:
            raise TypeError("Unserializable object {} of type {}".format(obj, type(obj)))

    return json.dumps(obj, default=from_entity)
