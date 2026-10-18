#!moo verb @auditlog auditlog --on $wizard --dspec either

# pylint: disable=return-outside-function,undefined-variable

"""
Staff command: show the most recent consequential actions from the audit log.
``@auditlog`` lists the latest entries; ``@auditlog <player>`` filters to the
actions a given account took. Each entry's detail, such as a sanction's
``because`` reason or a report's text, follows it, indented.
"""

from moo.sdk import context, query_audit, account_for, lookup

# This verb runs as its Wizard owner, so it checks the player who typed it.
if not context.player.is_wizard():
    print("Permission denied.")
    return

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
    line = str(row)
    # The target's name is a snapshot, which may be a persona; show the account behind it.
    if row.target_id:
        try:
            held = account_for(lookup(row.target_id))
        except Exception:  # pylint: disable=broad-exception-caught
            held = None
        if held is not None:
            line += f" (acct {held.pk})"
    print(line)
    # The detail is free text from players and staff; print it plain and bounded.
    detail = str(row.detail or "").replace("[", "(").replace("]", ")").strip()[:500]
    for part in detail.splitlines():
        print(f"    {part}")
