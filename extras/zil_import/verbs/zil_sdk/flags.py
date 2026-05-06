#!moo verb flag set_flag getp --on "Zork Root"
# pylint: disable=return-outside-function,undefined-variable
"""
Property/flag helpers for ZIL game objects.

flag:     args[0] = property name → bool (False if missing)
set_flag: args[0] = property name, args[1] = value
getp:     args[0] = property name [, args[1] = default]
          ZIL's ``<GETP obj prop>`` returns 0 for missing properties; this
          helper lets translated code avoid ``NoSuchPropertyError``.

``obvious`` is intrinsic on Object (a model field, not a Property), so
both reads and writes route through attribute access.

Translated routines call these as methods on the target object, e.g.
``obj.flag("openable")``, ``obj.set_flag("obvious", True)``,
``obj.getp("strength")``.
"""

from moo.sdk import NoSuchPropertyError

if verb_name == "set_flag":
    name = args[0]
    value = bool(args[1])
    if name == "obvious":
        this.obvious = value
        this.save()
    elif name == "invisible":
        # ZIL ``INVISIBLE`` flag inverts ``obvious``: setting INVISIBLE
        # hides from the parser, clearing it reveals.  Routing through
        # the intrinsic field keeps the parser's dobj search consistent
        # with what translated routines like RUG-FCN expect after a
        # ``<FCLEAR obj ,INVISIBLE>``.
        this.obvious = not value
        this.save()
    else:
        this.set_property(name, value)
elif verb_name == "getp":
    name = args[0]
    default = args[1] if len(args) > 1 else None
    if name == "obvious":
        return this.obvious
    if name == "invisible":
        return not this.obvious
    try:
        return this.get_property(name)
    except NoSuchPropertyError:
        return default
else:
    name = args[0]
    if name == "obvious":
        return bool(this.obvious)
    if name == "invisible":
        return not this.obvious
    try:
        return bool(this.get_property(name))
    except NoSuchPropertyError:
        return False
