#!moo verb look --on "room class"

from moo.core import api

qs = api.parser.this.properties.filter(name="description")
if qs:
    print(qs[0].value)
else:
    print("No description.")
