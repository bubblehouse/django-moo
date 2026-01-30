#!moo verb test-args-parser --on "player class" --dspec none

# pylint: disable=return-outside-function,undefined-variable

from moo.core import api

if api.parser is not None:
    print("PARSER")
