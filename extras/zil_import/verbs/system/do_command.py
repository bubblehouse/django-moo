#!moo verb do_command --on "System Object"
# pylint: disable=return-outside-function,undefined-variable
"""
LambdaMOO `$do_command` pre-dispatch hook for ZIL games.

Called by `moo/core/parse.py:interpret()` before normal verb dispatch.

This hook handles three ZIL-specific responsibilities:

1.  Per-turn daemon tick (i-river drift, i-lantern dim, etc.) so vehicle
    moves before the dispatched verb runs.
2.  Forwarding to `preturnfunc` (ZIL M-BEG) on the player's location and
    on any underlying physical room when the location is a vehicle.  A
    truthy return short-circuits dispatch (the M-BEG handler claimed it).
3.  Late dobj resolution for scenery atoms listed in the room's
    ``global_scenery`` property (LOCAL-GLOBALS) and for objects nested
    inside open containers in the same room.  This is the game-side
    replacement for an ``Object.find()`` patch that was reverted from
    moo-core; doing it here keeps all ZIL-shaped behavior inside the
    zork1 bootstrap.

The translator emits per-object/per-room ``preturnfunc`` verbs from ZIL
M-BEG clauses (see ``extras/zil_import/translator.py``'s ``_M_TO_VERB``).
"""

from moo.sdk import context, NoSuchPropertyError, NoSuchObjectError, lookup

player = context.player
loc = player.location
if loc is None:
    return False

# Tick the queue FIRST so per-turn daemons (i-river drift, i-lantern
# dim, etc.) fire before preturnfunc and main dispatch.  This lets the
# daemon's side-effects (a vehicle moving to a new room) be visible to
# preturnfunc and the dispatched verb — so e.g. ``go east`` from RIVER-4
# at the drift-trigger turn lands the player at the post-drift room
# rather than failing because the boat's still at RIVER-4.  ZIL's
# CLOCKER runs post-dispatch in the original; we can't hook there
# without a parse.py change, but pre-dispatch tick still gives the
# daemon a turn to fire on every command.
_.tick()

# Re-read player.location after tick — i-river may have moved the
# boat (and player with it).
loc = player.location
if loc is None:
    return False
try:
    is_vehicle = bool(loc.get_property("vehicle"))
except NoSuchPropertyError:
    is_vehicle = False

player_verb_arg = args[0] if args else None

if is_vehicle:
    if loc.has_verb("preturnfunc"):
        if loc.invoke_verb("preturnfunc", "M-BEG", player_verb_arg):
            return True
    physical_room = loc.location
else:
    physical_room = loc

if physical_room is not None and physical_room.has_verb("preturnfunc"):
    if physical_room.invoke_verb("preturnfunc", "M-BEG", player_verb_arg):
        return True

# --- Late dobj resolution for scenery and open-container peek ---
# When the parser failed to resolve dobj from the player's normal scope
# (caller, inventory, location.contents), give the room a chance via:
#   (a) ``global_scenery`` atoms listed on the room (LOCAL-GLOBALS) and
#   (b) any open container in the room (so ``take leaflet`` works while
#       the mailbox is open).
# The parser reads ``self.dobj`` inside ``get_search_order`` *after*
# ``__init__`` returns, so mutating it here is well-defined: the dobj we
# set will appear in the verb-dispatch search order naturally.
parser = context.parser
if parser is not None and parser.dobj is None and parser.dobj_str:
    needle = parser.dobj_str.lower()

    # Areas to scan: the physical room always; the vehicle (if any) too.
    areas = []
    if is_vehicle and loc is not None and loc is not physical_room:
        areas.append(loc)
    if physical_room is not None:
        areas.append(physical_room)

    found = None
    for area in areas:
        if found is not None:
            break

        # Scenery pass: ZIL's LOCAL-GLOBALS list lives on the room as
        # ``global_scenery`` (a list of UPPER-KEBAB atoms).  Each atom
        # resolves to a real Object via the lower-snake alias the
        # generator adds at bootstrap time.
        try:
            scenery_atoms = area.get_property("global_scenery") or []
        except NoSuchPropertyError:
            scenery_atoms = []
        for atom in scenery_atoms:
            try:
                candidate = lookup(str(atom).lower().replace("-", "_"))
            except NoSuchObjectError:
                continue
            # Skip invisible scenery (obvious=False covers both ZIL
            # NDESCBIT and INVISIBLE flags).  When a verb like move-rug
            # clears INVISIBLE, the trap door's obvious flips to True and
            # this hook starts finding it.
            if not bool(candidate.obvious):
                continue
            cname = (candidate.name or "").lower()
            if cname == needle:
                found = candidate
                break
            for alias_row in candidate.aliases.all():
                if alias_row.alias.lower() == needle:
                    found = candidate
                    break
            if found is not None:
                break
        if found is not None:
            break

        # Open-container peek: walk direct contents of the area, and for
        # any container whose ``open`` flag is True, search its contents
        # by name and aliases.  ZIL's parser sees through open containers
        # in the same room as the player.
        for container in area.contents.all():
            try:
                is_open = bool(container.get_property("open"))
            except NoSuchPropertyError:
                is_open = False
            if not is_open:
                continue
            for inner in container.contents.all():
                # Skip hidden-placement (under/behind) — matches the
                # ``exclude_hidden_placement`` behavior of Object.find.
                if inner.placement_prep in ("under", "behind"):
                    continue
                iname = (inner.name or "").lower()
                if iname == needle:
                    found = inner
                    break
                for alias_row in inner.aliases.all():
                    if alias_row.alias.lower() == needle:
                        found = inner
                        break
                if found is not None:
                    break
            if found is not None:
                break

    if found is not None:
        parser.dobj = found
        if found.name:
            parser.dobj_str = found.name

return False
