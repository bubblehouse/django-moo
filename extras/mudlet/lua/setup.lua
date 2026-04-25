-- Setup wizard for the djangomoo Mudlet package.
--
-- Usage:
--   dmsetup show                       -- print current settings
--   dmsetup host moo.example.com
--   dmsetup port 8022
--   dmsetup username phil
--   dmsetup local-port 8023
--   dmsetup auth password|key|agent
--   dmsetup key-file ~/.ssh/id_ed25519
--   dmsetup write-sshelnet             -- write the matching sshelnet YAML

djangomoo = djangomoo or {}
djangomoo.setup = djangomoo.setup or {}

local M = djangomoo.setup
local bridge_config = djangomoo.bridge_config

local function expandHome(p)
	if not p or p == "" then return p end
	if p:sub(1, 2) == "~/" then
		return (os.getenv("HOME") or "") .. p:sub(2)
	end
	return p
end

local function shellQuote(s)
	return "'" .. tostring(s):gsub("'", "'\\''") .. "'"
end

local FIELDS = {
	["host"] = "host",
	["port"] = "port",
	["username"] = "username",
	["local-port"] = "local_port",
	["local_port"] = "local_port",
	["auth"] = "auth_method",
	["key-file"] = "key_file",
	["key_file"] = "key_file",
	["term-type"] = "term_type",
	["term_type"] = "term_type",
	["editor"] = "editor_command",
	["editor-command"] = "editor_command",
	["editor_command"] = "editor_command",
}

local INT_FIELDS = { port = true, local_port = true }
local AUTH_VALUES = { password = true, key = true, agent = true }

local function show()
	local cfg = bridge_config.load()
	cecho("\n<DimGrey>[djangomoo setup]<reset> current settings:\n")
	cecho(string.format("  host        = %s\n", tostring(cfg.host)))
	cecho(string.format("  port        = %s\n", tostring(cfg.port)))
	cecho(string.format("  username    = %s\n", tostring(cfg.username)))
	cecho(string.format("  local_port  = %s\n", tostring(cfg.local_port)))
	cecho(string.format("  auth_method = %s\n", tostring(cfg.auth_method)))
	cecho(string.format("  key_file    = %s\n", tostring(cfg.key_file)))
	cecho(string.format("  term_type   = %s\n", tostring(cfg.term_type)))
	cecho(string.format("  editor      = %s\n", tostring(cfg.editor_command)))
	local ok, missing = bridge_config.isComplete(cfg)
	if ok then
		cecho("\n<green>configuration is complete.<reset> run <yellow>dmconnect<reset> to connect.\n")
	else
		cecho(string.format("\n<yellow>missing: %s<reset>\n", missing))
	end
end

function M.set(field, value)
	local key = FIELDS[field]
	if not key then
		cecho(string.format("\n<red>[djangomoo]<reset> unknown field %q\n", field))
		return
	end
	if INT_FIELDS[key] then
		local n = tonumber(value)
		if not n then
			cecho(string.format("\n<red>[djangomoo]<reset> %s must be a number\n", field))
			return
		end
		value = n
	end
	if key == "auth_method" and not AUTH_VALUES[value] then
		cecho("\n<red>[djangomoo]<reset> auth must be one of: password, key, agent\n")
		return
	end
	if key == "key_file" then
		value = expandHome(value)
	end
	local cfg = bridge_config.load()
	cfg[key] = value
	bridge_config.save(cfg)
	cecho(string.format("\n<DimGrey>[djangomoo]<reset> %s = %s\n", key, tostring(value)))
end

local function emitSshelnetYAML(profile_name, cfg)
	local lines = { "profiles:" }
	table.insert(lines, "  " .. profile_name .. ":")
	table.insert(lines, string.format("    host: %s", cfg.host))
	table.insert(lines, string.format("    port: %d", cfg.port))
	table.insert(lines, string.format("    username: %s", cfg.username))
	table.insert(lines, string.format("    local_port: %d", cfg.local_port))
	table.insert(lines, string.format("    term_type: %s", cfg.term_type or "xterm-256-basic"))
	table.insert(lines, "    auth:")
	if cfg.auth_method == "key" and cfg.key_file and cfg.key_file ~= "" then
		table.insert(lines, string.format("      key_file: %s", cfg.key_file))
	elseif cfg.auth_method == "agent" then
		table.insert(lines, "      use_agent: true")
	end
	return table.concat(lines, "\n") .. "\n"
end

function M.sshelnetProfileName()
	return "mudlet-" .. (getProfileName() or "default")
end

-- Mirror Go's os.UserConfigDir() per-platform behavior, since sshelnet
-- (a Go binary) uses that to find its config.yaml. Without this match,
-- the bridge would write to one path and sshelnet would read from
-- another, silently leaving the profile undiscoverable.
local function sshelnetConfigDir()
	local osn = getOS()
	if osn == "mac" then
		local home = os.getenv("HOME") or ""
		return home .. "/Library/Application Support/sshelnet"
	elseif osn == "windows" then
		local appdata = os.getenv("APPDATA") or (os.getenv("USERPROFILE") or "") .. "/AppData/Roaming"
		return appdata .. "/sshelnet"
	else
		local xdg = os.getenv("XDG_CONFIG_HOME")
		if xdg and xdg ~= "" then
			return xdg .. "/sshelnet"
		end
		local home = os.getenv("HOME") or ""
		return home .. "/.config/sshelnet"
	end
end

function M.writeSshelnet()
	local cfg = bridge_config.load()
	local ok, missing = bridge_config.isComplete(cfg)
	if not ok then
		cecho(string.format("\n<red>[djangomoo]<reset> setup incomplete (missing %s). run <yellow>dmsetup show<reset>.\n", missing))
		return false
	end
	local cfg_dir = sshelnetConfigDir()
	if not lfs or not lfs.attributes(cfg_dir) then
		os.execute("mkdir -p " .. shellQuote(cfg_dir))
	end
	local path = cfg_dir .. "/config.yaml"
	local f, err = io.open(path, "w")
	if not f then
		cecho(string.format("\n<red>[djangomoo]<reset> could not open %s: %s\n", path, tostring(err)))
		return false
	end
	f:write(emitSshelnetYAML(M.sshelnetProfileName(), cfg))
	f:close()
	cecho(string.format("\n<DimGrey>[djangomoo]<reset> wrote sshelnet profile %q to %s\n",
		M.sshelnetProfileName(), path))
	return true
end

local function help()
	cecho([[

<DimGrey>[djangomoo setup]<reset>
  <yellow>dmsetup show<reset>                       view current settings
  <yellow>dmsetup host<reset> <hostname>            SSH server host
  <yellow>dmsetup port<reset> <number>              SSH server port (default 8022)
  <yellow>dmsetup username<reset> <name>            SSH login
  <yellow>dmsetup local-port<reset> <number>        local TCP port for the proxy
  <yellow>dmsetup auth<reset> password|key|agent    SSH auth method
  <yellow>dmsetup key-file<reset> <path>            path to private key (auth=key)
  <yellow>dmsetup term-type<reset> <string>         SSH terminal type
  <yellow>dmsetup editor<reset> <command>          editor for @edit ({file} placeholder)
  <yellow>dmsetup write-sshelnet<reset>             write the matching sshelnet YAML

]])
end

function M.dispatch(subcommand, value)
	if not subcommand or subcommand == "" or subcommand == "help" then
		help()
		return
	end
	if subcommand == "show" then
		show()
		return
	end
	if subcommand == "write-sshelnet" or subcommand == "write_sshelnet" then
		M.writeSshelnet()
		return
	end
	if not value or value == "" then
		cecho(string.format("\n<red>[djangomoo]<reset> dmsetup %s requires a value\n", subcommand))
		return
	end
	M.set(subcommand, value)
	if subcommand == "host" or subcommand == "port" or subcommand == "username"
		or subcommand == "local-port" or subcommand == "local_port" then
		M.writeSshelnet()
	end
end

return M
