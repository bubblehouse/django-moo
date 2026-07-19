#!moo verb @destroy --on $builder --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Permanently delete an object (spec 200, item K).  Unlike ``@recycle`` (which is
now a reversible soft-recycle), ``@destroy`` is irreversible — the object and
its inbound references are gone for good.
"""

from moo.sdk import context, destroy

if not context.parser.has_dobj_str():
    print("[yellow]What do you want to destroy?[/yellow]")
    return

obj = context.parser.get_dobj(lookup=True)
name = obj.title()
# Let destroy's own errors surface — a permission denial (AccessError is a
# PermissionError) is rendered by the task runner with its real reason, rather
# than masked behind a generic "Error destroying".
destroy(obj)
print(f"[red]Destroyed {name} permanently.[/red]")
