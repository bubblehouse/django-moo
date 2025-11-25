#!moo verb title --on "Root Class"

"""
This verb is used to get the name property of this object.

One example where it might be useful to redefine this verb is if you want to add an honorificor descriptive phrase to
the end of your name. By overriding the `title` verb, you can append anything you like to the `name` property of the
object.
"""

if not this.name:
    return str(this)  # pylint: disable=return-outside-function. # type: ignore
return this.name  # pylint: disable=return-outside-function. # type: ignore
