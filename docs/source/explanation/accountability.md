# Accountability, safety, and world-build hooks

A public, user-programmable world faces abuse surfaces a fresh database lacks —
the things LambdaCore grew over years. DjangoMOO's `default` dataset provides a
set of engine and `default`-level primitives for them, alongside ergonomic
seams that themed content packs build on. Each is generically useful to any
`default` game, not tied to one world.

## The account is the unit of identity

Identity has three conceptual layers: the **account** (durable, staff-visible),
the **avatar** (the in-world `$player` object), and any **persona** a player has
"become". The account is the {class}`~moo.core.models.auth.Player` row — its
`pk` is a stable id distinct from any display name. Moderation keys to the
account, so a name change or a recycled avatar never breaks traceability, and a
ban targets the human rather than a discardable avatar. Resolve between the two
with {func}`moo.sdk.account_for` and {func}`moo.sdk.avatars_of`.

An account carries a `status` (`active`, `guest`, `suspended`, `banned`), an
optional `registered_identity` (a durable identifier bound at registration), and
a `suspended_until` deadline. A bound `registered_identity` is unique per site,
so one human's identifier cannot be claimed by two accounts — which matters
because a ban blacklists by identity and must key to exactly one account.

## Provenance is always on

Every message published to a player carries a server-computed provenance triple
(`origin`, `verb`, `owner`), recorded **always** — independent of the
recipient's `@paranoid` setting, which becomes the *view* of an ever-present
record rather than a switch that turns recording on. The triple is read from the
in-memory caller stack, so it stays a tag-and-id on the hot path; a full
caller-stack capture for a report happens only on demand via
{func}`moo.sdk.capture_provenance_stack`.

Sanctioned output also carries a structural `kind` tag (`say`/`emote`/`system`/
`persona`) applied server-side, so a user-authored line cannot present as a
system line or as another actor. The `system` kind requires a wizard
*initiator*, making it unforgeable from an ordinary user's verb even though the
emitting primitive ({func}`moo.sdk.notify`) runs as a wizard-owned verb.

## Flooding, sanctions, and onboarding

A per-account broadcast budget ({func}`moo.sdk.broadcast_allowed`, tuned by
`MOO_BROADCAST_RATE_LIMIT` or the System Object `broadcast_rate_limit` knob)
drops a runaway verb's broadcast lines while never counting a player's own
output — the target is flooding, not verbosity.

Staff sanctions sit above `@gag` and `@eject`: a reversible
{func}`moo.sdk.suspend` and a scarring {func}`moo.sdk.ban` that blacklists the
account's durable identity so the same human cannot simply re-register. Both key
to the account and neither can target staff; the SSH login path consults
{func}`moo.sdk.account_login_blocked`, which also clears a suspension whose
deadline has passed so a lapsed account does not read as suspended forever.

Onboarding runs guest → registered: {func}`moo.sdk.provision_guest` creates a
non-persistent `$guest` who can explore and talk but not build or own, and
{func}`moo.sdk.register` binds a durable identity through a pluggable verifier
(`MOO_REGISTRATION_VERIFIER`) before build rights are granted
({func}`moo.sdk.require_registered`). The built-in verifier is deliberately
permissive — it normalizes the identity but does not prove the registrant
controls it — so a deployment that exposes `@register` and relies on bans
holding must point `MOO_REGISTRATION_VERIFIER` at a real verifier (email
round-trip, SSO) first.

Consequential actions (create, recycle, destroy, owner/permission change,
sanctions) are recorded to an append-only audit log via
{func}`moo.sdk.record_action`; only player-initiated actions are logged, so
bootstrap and system activity never floods it. The log is enforced append-only —
a row cannot be modified or deleted through the ORM (the attempt raises
`AppendOnlyError`), so the trail stays tamper-evident. Staff query it with
`@auditlog`.

## Recovery and the escape guarantee

`@recycle` is a reversible **soft-recycle**: the object is hidden from the
site-scoped manager but keeps its id and inbound references, so `@restore` can
bring it back; `@destroy` remains for permanent removal, and
{func}`moo.sdk.sweep_recycled` purges anything left past the retention window. A
regular builder's `@restore` is scoped to their own recycled objects (a wizard
may restore any), so naming another builder's object neither reveals it nor
forces a permission error.

`home` is an engine escape guarantee: {func}`moo.sdk.send_home` forces the move
to the player's home (or `$player_start`), bypassing the destination's
`accept`/locks/verbs so a player can never be trapped by a room owner.
{func}`moo.sdk.check_room_connectivity` is the build-time guard that flags a
dead-end or one-way room before players fall into it.

## World-build hooks

Themed rooms compose their rendering without copying core verbs, through
overridable `$room` hooks: `look_description()`, `show_compass()`,
`hide_from_contents(obj)`, and `tell_contents_extra()`. A lattice or overworld
room can resolve exits by a function over position with the `procedural_exit()`
hook, which routes computed moves through the standard exit messaging/GMCP path
so they behave identically to stored exits. Quest, achievement, and tutorial
systems observe gameplay through the `on_player_action(player, action, data)`
hook the common player verbs emit after they succeed. Data-generated worlds
resolve objects by a stable external key in O(1) with
{func}`moo.sdk.get_or_create_by_key`.

## Compute bounds

Each verb task is bounded by the Celery wall-clock kill and, more finely, by a
per-task loop budget (`MOO_TICK_BUDGET`): a runaway loop aborts with
`TickLimitError` before it burns the whole time budget. The budget is
deliberately generous — a legitimate sweep over a large world should never trip
it.

## Object quota (already enforced)

Object quota needs no new work: `create()` raises `QuotaError` and decrements
the owner's `ownership_quota`, and recycling refunds it (a soft-recycle refunds
once, and a later hard-destroy of an already-recycled object does not
double-refund). A future *measured* (byte) quota in addition to the object count
is a possible later refinement, not a requirement.
