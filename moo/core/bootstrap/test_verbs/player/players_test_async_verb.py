#!moo verb test-async-verb --on "player class" --dspec this

from moo.core import api, invoke

counter = 1
if args and len(args):  # pylint: disable=undefined-variable  # type: ignore
    counter = args[1] + 1  # pylint: disable=undefined-variable  # type: ignore

if counter < 10:
    return counter  # pylint: disable=return-outside-function  # type: ignore
