#!moo verb look --on "player class" --ability

from moo.core import api

qs = api.caller.location.properties.filter(name="description")
if qs:
    print(qs[0].value)
else:
    print("No description.")
