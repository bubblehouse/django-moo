#!moo verb test-args-parser --on "player class" --dspec this

from moo.core import api

if api.parser is not None:
    print("PARSER")
