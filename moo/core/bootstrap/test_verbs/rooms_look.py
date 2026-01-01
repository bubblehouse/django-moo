#!moo verb look --on "room class"

qs = this.properties.filter(name="description")  # pylint: disable=undefined-variable. # type: ignore
if qs:
    print(qs[0].value)
else:
    print("No description.")
