#!moo verb test-args-parser --on "player class" --dspec none

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context

if context.parser is not None:
    print("PARSER")
