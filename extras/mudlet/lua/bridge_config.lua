-- Persistent connection settings for the djangomoo Mudlet package.
--
-- Stored as a Lua table at getMudletHomeDir() .. "/djangomoo_bridge.lua"
-- (one file per Mudlet profile, since getMudletHomeDir is profile-scoped).
-- Password is intentionally never persisted.

djangomoo = djangomoo or {}
djangomoo.bridge_config = djangomoo.bridge_config or {}

local M = djangomoo.bridge_config

local CONFIG_PATH = getMudletHomeDir() .. "/djangomoo_bridge.lua"

-- Per-OS default editor command. The {file} placeholder is replaced with
-- the temp file path before spawn. Each default uses a "wait until closed"
-- mode so the bridge can detect when the user is done editing:
--   macOS:   open -W -t <file>      (TextEdit / default text editor, blocks)
--   Linux:   xdg-open <file>        (best-effort; may not block — bridge falls
--                                    back to mtime polling for non-waiting opens)
--   Windows: notepad <file>         (blocks naturally until closed)
local function defaultEditorCommand()
	local osn = getOS()
	if osn == "mac" then return "open -W -t {file}" end
	if osn == "windows" then return "notepad {file}" end
	return "xdg-open {file}"
end

local DEFAULTS = {
	port = 8022,
	local_port = 8023,
	auth_method = "password",
	term_type = "xterm-256-basic",
	editor_command = nil,  -- filled lazily in load() so getOS() is safe
}

local function fileExists(path)
	local f = io.open(path, "r")
	if f then
		f:close()
		return true
	end
	return false
end

function M.path()
	return CONFIG_PATH
end

function M.load()
	local cfg = {}
	if fileExists(CONFIG_PATH) then
		table.load(CONFIG_PATH, cfg)
	end
	for k, v in pairs(DEFAULTS) do
		if cfg[k] == nil then
			cfg[k] = v
		end
	end
	if cfg.editor_command == nil or cfg.editor_command == "" then
		cfg.editor_command = defaultEditorCommand()
	end
	return cfg
end

function M.save(cfg)
	table.save(CONFIG_PATH, cfg)
end

function M.isComplete(cfg)
	cfg = cfg or M.load()
	if not cfg.host or cfg.host == "" then
		return false, "host"
	end
	if not cfg.port or cfg.port == 0 then
		return false, "port"
	end
	if not cfg.username or cfg.username == "" then
		return false, "username"
	end
	if not cfg.local_port or cfg.local_port == 0 then
		return false, "local_port"
	end
	if cfg.auth_method == "key" and (not cfg.key_file or cfg.key_file == "") then
		return false, "key_file"
	end
	return true
end

return M
