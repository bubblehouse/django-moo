from termiverse.core import api

qs = api.caller.properties.filter(name="description")
if qs:
    print(qs[0])
else:
    print("No description.")
