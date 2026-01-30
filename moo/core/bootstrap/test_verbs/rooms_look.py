#!moo verb look --on "room class"

# pylint: disable=return-outside-function,undefined-variable

qs = this.properties.filter(name="description")  # pylint: disable=undefined-variable. # type: ignore
if qs:
    print(qs[0].value)
else:
    print("No description.")
