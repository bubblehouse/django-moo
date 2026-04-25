# DjangoMOO Mudlet Package

A small bridge package for [Mudlet](https://www.mudlet.org/) that wires
DjangoMOO's `gmcp.Room.Info` events into the room-detection slots of
Mudlet's bundled "generic mapper" script.

Without this package, Mudlet's mapper falls back to its default
text-trigger mode and never picks up the structured GMCP payload
DjangoMOO emits — so `map basics` shows "room name ❌" and `start
mapping` errors with "Room detection not yet working."

## Installation

1. In Mudlet, open *Settings → Package Manager*.
2. Click *Install*, then select `djangomoo_mapper_bridge.mpackage`.
3. Reconnect (or move once, so a fresh `gmcp.Room.Info` arrives).
4. Run `map basics` — both "room name" and "exits" should now show ✅.
5. Run `start mapping <area name>` to begin.

The package registers a single event handler. It does not modify any of
Mudlet's bundled scripts; uninstall via the Package Manager removes
exactly what it added.

## What it does

The handler fires on every `gmcp.Room.Info` event, feeds the payload
into the generic mapper's documented external-script integration slots,
and raises `onNewRoom` so the mapper's existing pipeline takes over:

| GMCP field             | Mapper slot          |
|------------------------|----------------------|
| `gmcp.Room.Info.name`  | `map.prompt.room`    |
| `gmcp.Room.Info.exits` | `map.prompt.exits`   |

The exits dict is converted from IRE-style short codes (`n`, `ne`, `e`,
…) to long direction names (`north`, `northeast`, `east`, …) joined as
a space-separated string — the format `handle_exits()` expects. Custom-
named exits (`ladder`, `portal`, etc.) round-trip unchanged.

After populating those slots, the bridge raises `onNewRoom`, which
triggers `handle_exits → capture_room_info → move_map`. The mapper
already auto-captures the player's movement command (e.g., `go east`)
into its `move_queue` via the `sysDataSendRequest` event, so room
linking happens correctly: existing rooms are matched and set, new
rooms are created and linked to the previous one in the direction of
travel.

The full Room.Info payload shape DjangoMOO emits is documented in
[`docs/source/how-to/accessibility.md`](../../docs/source/how-to/accessibility.md).

## Source layout

| File                            | Purpose                                                  |
|---------------------------------|----------------------------------------------------------|
| `djangomoo_mapper_bridge.xml`   | The Mudlet script (`<MudletPackage>` / `<ScriptPackage>`). |
| `config.lua`                    | Package metadata read by Mudlet's Package Manager.       |
| `build.sh`                      | Zips the above into `djangomoo_mapper_bridge.mpackage`.  |
| `djangomoo_mapper_bridge.mpackage` | Built artifact, committed for direct download.        |

## Rebuilding

```sh
./build.sh
```

Bumps nothing automatically — update `version` in `config.lua` if you
ship behavioural changes.

## Other clients

There is no universal mapping protocol that "just works" across MUD
clients. MUSHclient, TinTin++, ZMUD/CMUD, and BlowTorch all need their
own equivalent shim. The Room.Info payload shape documented in the
accessibility guide is the contract — pick whatever scripting hook your
client provides and copy the fields into its mapper state.
