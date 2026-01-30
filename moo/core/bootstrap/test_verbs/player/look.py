#!moo verb look --on "player class" --dspec either

# pylint: disable=return-outside-function,undefined-variable

from moo.core import api

qs = api.caller.location.properties.filter(name="description")
if qs:
    print(qs[0].value)
else:
    print("No description.")
