-- DjangoMOO -> Mudlet generic mapper bridge.
--
-- DjangoMOO emits the IRE-style Room.Info GMCP event on connect and after
-- every move. This module feeds that payload into the mapper's documented
-- external-script slots (map.prompt.room / map.prompt.exits) and raises
-- onNewRoom, so the mapper's existing pipeline (capture_room_info ->
-- move_map -> find_link / find_me) takes over.
--
-- See docs/source/how-to/accessibility.md in the DjangoMOO repo for the
-- exact Room.Info payload shape this expects.

djangomoo = djangomoo or {}
djangomoo.mapper = djangomoo.mapper or {}

local M = djangomoo.mapper

local SHORT_TO_LONG = {
	n = "north", s = "south", e = "east", w = "west",
	ne = "northeast", nw = "northwest",
	se = "southeast", sw = "southwest",
	u = "up", d = "down",
	["in"] = "in", out = "out",
}

local warned_no_mapper = false
local warned_not_mapping = false

local function warn(msg)
	cecho("\n<yellow>[djangomoo]</yellow> " .. msg .. "\n")
end

function M.handle_room_info()
	if not gmcp or not gmcp.Room or not gmcp.Room.Info then
		return
	end
	if not map then
		if not warned_no_mapper then
			warned_no_mapper = true
			warn("Mudlet's generic-mapper package is not installed. Mapping is disabled.")
			warn("Install it via Settings -> Package Manager. The bundled file is " ..
			     "`generic_mapper.mpackage` inside your Mudlet install dir " ..
			     "(macOS: /Applications/mudlet.app/Contents/Resources/mudlet-lua/lua/generic-mapper/).")
		end
		return
	end

	local info = gmcp.Room.Info

	local parts = {}
	if type(info.exits) == "table" then
		for direction, _ in pairs(info.exits) do
			table.insert(parts, SHORT_TO_LONG[direction] or direction)
		end
	end
	local exits_str = table.concat(parts, " ")

	map.prompt = map.prompt or {}
	map.prompt.room = info.name or ""
	map.prompt.exits = exits_str

	raiseEvent("onNewRoom", exits_str)

	if not map.mapping and not warned_not_mapping then
		warned_not_mapping = true
		warn("Generic mapper is installed but mapping is off. " ..
		     "Run `start mapping <area name>` to begin building the map.")
	end
end

function M.resetWarnings()
	warned_no_mapper = false
	warned_not_mapping = false
end

return M
