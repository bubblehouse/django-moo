#!moo verb inspect --on "player class" --dspec this

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context

qs = context.caller.location.properties.filter(name="description")
if qs:
    print(qs[0].value)
else:
    print("No description.")
