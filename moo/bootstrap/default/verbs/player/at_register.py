#!moo verb @register register_identity --on $player --dspec any

# pylint: disable=return-outside-function,undefined-variable

"""
Self-service: bind a durable identity (email or another deployment-chosen
verifier) to your account.  Registration is the gate to build rights and the
thing a ban can enforce against, so it is required before promotion past guest.
"""

from moo.sdk import context, account_for, register

if not context.parser.has_dobj_str():
    print("Usage: @register <email-or-identity>")
    return

identity = context.parser.get_dobj_str()
account = account_for(context.player)
if account is None:
    print("You have no account to register.")
    return

try:
    register(account, identity)
except Exception as err:  # pylint: disable=broad-exception-caught
    print(str(err))
    return

print("Registration complete — you now have a durable identity.")
