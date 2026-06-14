#!moo verb hide_from_contents --on $room --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Overridable hook (spec 200, item A): return True to omit ``what`` from this
room's contents listing — e.g. scenery a themed room renders inside its own
description.  Default False (show everything as usual).
"""

return False
