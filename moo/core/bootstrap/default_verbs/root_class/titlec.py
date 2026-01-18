#!moo verb title --on "Root Class"

"""
This verb performs the same function as the `title` verb, but returns a capitalised version of the name property of the
object, using the string.capitalize() method.

"""

if not this.name:
    return str(this)  # pylint: disable=return-outside-function. # type: ignore
return this.name.capitalize()  # pylint: disable=return-outside-function. # type: ignore
