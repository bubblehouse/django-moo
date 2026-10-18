#!moo verb sanction_args --on $wizard

# pylint: disable=return-outside-function,undefined-variable

"""
Read a staff sanction command: ``<command> <player> [for <hours>] [because <reason>]``.

Return a tuple ``(target, hours, reason)``. ``target`` is the named Object, or
None when the command names nobody or the name matches nothing (this verb then
prints why). ``hours`` is the text after ``for``, or None. ``reason`` is the
plain text after ``because``, or "". The reason goes into the audit entry, so
staff can cite a house rule on the sanction itself.
"""

from moo.sdk import context, lookup, NoSuchObjectError

words = list(context.parser.words[1:])
reason = ""
if "because" in words:
    cut = words.index("because")
    # Staff read the audit log as console text; keep the reason plain and bounded.
    reason = " ".join(words[cut + 1 :]).strip().replace("[", "(").replace("]", ")")[:1000]
    words = words[:cut]
hours = None
if "for" in words:
    cut = words.index("for")
    hours = " ".join(words[cut + 1 :]).strip() or None
    words = words[:cut]
name = " ".join(words).strip()
if not name:
    return (None, hours, reason)
try:
    if name.startswith("#") and name[1:].isdigit():
        target = lookup(int(name[1:]))
    else:
        target = lookup(name)
except NoSuchObjectError:
    print(f"There is no one named {name!r}.")
    return (None, hours, reason)
return (target, hours, reason)
