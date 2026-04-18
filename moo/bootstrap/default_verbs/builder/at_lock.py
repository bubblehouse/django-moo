#!moo verb @lock --on $builder --dspec any --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Lock an object with a specified key. It first matches the direct object to get an
object reference number. If that succeeds, the `$lock_utils.parse_keyexp()` verb is called to parse the key expression
given for the lock. If that fails, a suitable error message is printed. Otherwise, the `key` property of the object
being locked is set to the returned value from the parsing verb. Again, any errors are reported to the invoking player.
"""

from moo.sdk import context

parser = context.parser

obj = parser.get_dobj()
expr = parser.get_pobj_str("with")

key = _.lock_utils.parse_keyexp(expr)
if key is None:
    print("That doesn't look like a valid key expression.")
    return
obj.set_property("key", key)
