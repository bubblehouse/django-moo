mpackage = [[djangomoo_mapper_bridge]]
author = [[DjangoMOO Project]]
title = [[DjangoMOO bridge for Mudlet's generic mapper.]]
description = [[# DjangoMOO Mapper Bridge

Connects DjangoMOO's `gmcp.Room.Info` event stream to the room-detection
slots the bundled "generic mapper" script reads (`map.currentName`,
`map.currentExits`, `map.currentArea`).

After installing this package, no other configuration is needed:

1. Connect to your DjangoMOO server through Mudlet.
2. Move once so a fresh `gmcp.Room.Info` event arrives.
3. Run `map basics` — both "room name" and "exits" should show ✅.
4. Run `start mapping <area name>` to begin.

The generic mapper script (`map basics`, `start mapping`, `map debug`,
etc.) is itself bundled with Mudlet — this package only supplies the
glue between GMCP and the mapper's internal state.

See the DjangoMOO project documentation for the exact Room.Info payload
shape this bridge consumes.
]]
version = [[1.3.1]]
created = "2026-04-25T00:00:00+00:00"
