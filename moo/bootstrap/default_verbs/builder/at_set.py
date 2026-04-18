#!moo verb @set --on $builder --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Add or update a property on an object.

Usage:
    @set <property> on <object> to <expression>

<object> may be a name, alias, $system-property, or #N object reference.
<expression> is evaluated in the verb sandbox (same rules as @eval), so
values may be Python literals or SDK calls:

    @set count on widget to 42
    @set name on widget to "Hello"
    @set owner on widget to lookup("$wizard")
    @set items on widget to [1, 2, 3]
    @set target on #123 to lookup("$wizard")

If the property does not exist it is created; otherwise its value is
updated.  The caller must have write permission on the target object.

Strings may be given with or without surrounding quotes — the command
lexer strips outer quotes, so `to "Hello"` and `to Hello` both store the
string "Hello".  Quoting is still useful when the value contains a bare
preposition word (on, with, from, etc.), since otherwise the parser will
split the command on it:

    @set msg on widget to "move on"
"""

from moo.sdk import context, lookup, moo_eval, set_task_perms, NoSuchObjectError

parser = context.parser

prop_name = parser.get_dobj_str().strip()

try:
    obj_ref = parser.get_pobj_str("on").strip()
    value_expr = parser.get_pobj_str("to")
except (TypeError, AttributeError, KeyError):
    print("Usage: @set <property> on <object> to <value>")
    return

if not prop_name or not obj_ref or not value_expr:
    print("Usage: @set <property> on <object> to <value>")
    return

try:
    if obj_ref.startswith("#"):
        target = lookup(int(obj_ref[1:]))
    else:
        target = lookup(obj_ref)
except (NoSuchObjectError, ValueError):
    print(f"I don't know the object '{obj_ref}'.")
    return

with set_task_perms(context.player):
    try:
        value = moo_eval(value_expr)
    except NameError:
        # The command lexer strips outer quotes, so `to "Hello"` arrives as
        # the bare identifier `Hello`.  Treat it as a literal string.
        value = value_expr
    except (TypeError, ValueError, SyntaxError) as e:
        print(f"Error evaluating value: {e}")
        return
    try:
        target.set_property(prop_name, value)
    except (TypeError, ValueError, AttributeError) as e:
        print(f"Error: {e}")
        return

print(f"{target.title()}.{prop_name} set to {value!r}")
