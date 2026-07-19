# -*- coding: utf-8 -*-
"""
Provenance and structurally-tagged output.

Every message published to a player carries a server-computed provenance triple
(``origin``, ``verb``, ``owner``) — recorded always, independent of the
recipient's ``@paranoid`` setting, which becomes the *view* of an always-present
record rather than a switch that turns recording on.  This is the safeguard the
rest of the safety set reads from: trustworthy attribution, spoof tracing, and
account-keyed moderation.

Output also carries a structural ``kind`` tag so the sanctioned forms
(``say``/``emote``/``system``/``persona``) are distinguishable by the client and
a user-authored line cannot present as a system line or as another actor.  The
``system`` kind is gated to a wizard *initiator* (``context.player``), so it is
unforgeable from an ordinary user's verb even though the emitting primitive runs
as a wizard-owned verb.
"""

from ..core.exceptions import UserError
from .context import context

#: The structural output tags the client renders distinctly.
OUTPUT_KINDS = ("text", "say", "emote", "system", "persona")

#: Kinds that only a wizard initiator may emit (forgery-protected).
PRIVILEGED_KINDS = ("system",)


def current_provenance():
    """Return the always-on provenance triple for the running task.

    See :func:`moo.core.current_provenance`.  Re-exported here so verb authors
    import it from ``moo.sdk`` like the rest of the API.
    """
    from ..core import current_provenance as _cp

    return _cp()


def capture_provenance_stack():
    """Return the full caller stack as a list of provenance frames.

    The expensive form, for a report or audit only — the hot path uses the
    single-frame :func:`current_provenance`.  Each frame is
    ``{"origin", "this", "verb", "owner"}`` with object pks.

    :return: list of frame dicts, outermost first
    """
    from ..core.code import ContextManager

    frames = []
    for frame in ContextManager.get("caller_stack"):
        this = frame.get("this")
        caller = frame.get("caller")
        frames.append(
            {
                "origin": this.pk if this is not None else None,
                "this": this.pk if this is not None else None,
                "verb": frame.get("verb_name"),
                "owner": caller.pk if caller is not None else None,
            }
        )
    return frames


def resolve_provenance_account(provenance):
    """Resolve a provenance triple's ``owner`` object to its account id.

    The report/audit-time step that turns the cheap object-pk record into an
    account-keyed one (G), so moderation keys to the human, not a discardable
    avatar.

    :param provenance: a triple from :func:`current_provenance`, or ``None``
    :return: the owning Player account id, or ``None``
    """
    from ..core.models import Object
    from .accounts import account_id_for

    if not provenance or provenance.get("owner") is None:
        return None
    owner = Object.objects.filter(pk=provenance["owner"]).first()
    return account_id_for(owner)


def notify(obj, message, kind="text"):
    """Send a structurally-tagged message to a player.

    The tagged-output counterpart to :func:`moo.sdk.write`: the ``kind`` is
    applied server-side and carried in the envelope so it cannot be spoofed by
    embedding markup in ``message``.  Like ``write``, this is a privileged
    primitive (wizard-owned verbs only); the sanctioned ``say``/``emote``/
    system verbs route through it.  The ``system`` kind additionally requires a
    wizard *initiator*, so an ordinary user's verb cannot wear it.

    :param obj: the player avatar Object to write to
    :param message: the payload (typically a string)
    :param kind: one of :data:`OUTPUT_KINDS`
    :raises UserError: on a bad kind, a non-wizard caller, or a non-wizard
        initiator attempting a privileged kind
    """
    from ..core import _publish_to_player

    if kind not in OUTPUT_KINDS:
        raise UserError(f"Unknown output kind {kind!r}; expected one of {OUTPUT_KINDS}.")
    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can emit tagged output.")
    if kind in PRIVILEGED_KINDS:
        initiator = context.player
        if initiator is None or not initiator.is_wizard():
            raise UserError(f"Only a wizard may emit {kind!r}-tagged output.")
    _publish_to_player(obj, message, kind=kind)
