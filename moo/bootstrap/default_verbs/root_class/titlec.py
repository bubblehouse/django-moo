#!moo verb titlec --on $root_class

# pylint: disable=return-outside-function,undefined-variable

"""
Perform the same function as the `title` verb, but return a capitalised version of the name property of the
object, using the string.capitalize() method.

"""

if not this.name:
    return str(this)
return this.name.capitalize()
