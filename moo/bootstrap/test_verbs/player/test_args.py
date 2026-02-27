#!moo verb test-args test_args --on "player class" --dspec this

# pylint: disable=return-outside-function,undefined-variable

from moo.core import context

if args is not None:  # pylint: disable=undefined-variable
    print(f"METHOD:{args}:{kwargs}")  # pylint: disable=undefined-variable
