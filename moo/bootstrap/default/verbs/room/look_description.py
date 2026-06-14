#!moo verb look_description --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Overridable hook (spec 200, item A): the room's prose description.

Default returns the ``description`` property.  A themed room ($zone, $poi, a
shop, a faction hall) overrides this to compose an area-sourced description
without copying the whole ``look_self`` verb.
"""

if this.has_property("description"):
    return this.get_property("description")
return ""
