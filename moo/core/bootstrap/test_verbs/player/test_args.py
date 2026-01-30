#!moo verb test-args --on "player class" --dspec this

# pylint: disable=return-outside-function,undefined-variable

from moo.core import api

if args is not None:  # pylint: disable=undefined-variable
    print(f"METHOD:{args}:{kwargs}")  # pylint: disable=undefined-variable
