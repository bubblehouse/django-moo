#!moo verb @lock_for_read lock_for_read --on $note --dspec this --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
This verb will lock the note with `object`. The note can only be read if the player is holding `object`, or
the `object` is the player trying to read the note. The note will remained locked until it is unlocked.
"""

from moo.core import context

keyexp = args[0] if args else context.parser.get_pobj_str("with")
this.set_property("read_key", _.lock_utils.parse_keyexp(keyexp.strip('"\'')))
