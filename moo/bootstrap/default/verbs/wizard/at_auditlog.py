#!moo verb @auditlog auditlog --on $wizard --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: show the most recent consequential actions from the audit log.
``@auditlog`` lists the latest entries; ``@auditlog <player>`` filters to the
actions a given account took.
"""

from moo.sdk import context, query_audit, account_for

if context.parser.has_dobj_str():
    target = context.parser.get_dobj(lookup=True)
    account = account_for(target)
    if account is not None:
        rows = query_audit(actor=account, limit=30)
    else:
        rows = query_audit(target=target, limit=30)
else:
    rows = query_audit(limit=30)

if not rows:
    print("No matching audit entries.")
    return

print("[bold]Recent actions (newest first):[/bold]")
for row in rows:
    print(str(row))
