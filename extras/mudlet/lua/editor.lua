-- DjangoMOO external-editor handoff (GMCP Editor package).
--
-- When the server detects this client supports the Editor package
-- (advertised in djangomoo.connection on connect via Core.Supports.Set),
-- it sends `Editor.Start { id, content, content_type, title }` instead
-- of trying to draw the prompt-toolkit TUI editor. We:
--   1. write the content to a temp file with a content_type-appropriate
--      extension so $EDITOR picks the right syntax,
--   2. spawn the user's configured editor (`bridge_config.editor_command`),
--   3. wait for the spawn to exit (via Mudlet's `isRunning()` polling, or
--      mtime polling for non-blocking openers like xdg-open),
--   4. read the file back and send `Editor.Save { id, content }` over GMCP.
-- If the user closes without saving, mtime is unchanged and we send
-- `Editor.Cancel { id }` to drop the server-side pending edit.

djangomoo = djangomoo or {}
djangomoo.editor = djangomoo.editor or {}

local M = djangomoo.editor
local bridge_config = djangomoo.bridge_config

local EXTENSIONS = {
	python = ".py",
	json = ".json",
	text = ".txt",
}

-- Sessions in flight, keyed by edit_id. We poll each one independently so
-- the user can stack multiple @edit calls in quick succession without one
-- swallowing another.
local sessions = {}

local function fileMtime(path)
	if lfs and lfs.attributes then
		local attr = lfs.attributes(path)
		if attr then return attr.modification end
	end
	-- Fallback: io.popen stat. macOS BSD stat differs from GNU; the -f form
	-- works on darwin, the -c form on linux. We pick by getOS().
	local cmd
	if getOS() == "mac" then
		cmd = "stat -f %m " .. ("'" .. path:gsub("'", "'\\''") .. "'")
	else
		cmd = "stat -c %Y " .. ("'" .. path:gsub("'", "'\\''") .. "'")
	end
	local p = io.popen(cmd .. " 2>/dev/null")
	if not p then return 0 end
	local out = (p:read("*l") or ""):match("(%d+)")
	p:close()
	return tonumber(out) or 0
end

local function readWholeFile(path)
	local f = io.open(path, "r")
	if not f then return nil end
	local data = f:read("*a")
	f:close()
	return data
end

local function writeWholeFile(path, content)
	local f = io.open(path, "w")
	if not f then return false end
	f:write(content or "")
	f:close()
	return true
end

local function tempFilePath(edit_id, content_type)
	local ext = EXTENSIONS[content_type] or ".txt"
	local tmpdir = os.getenv("TMPDIR") or "/tmp"
	if getOS() == "windows" then
		tmpdir = os.getenv("TEMP") or os.getenv("TMP") or "."
	end
	return tmpdir .. "/djangomoo-edit-" .. edit_id .. ext
end

-- Replace {file} placeholder in the editor command with a properly quoted
-- temp path. We don't shell-escape the rest of the command — the user
-- supplies it and is expected to know what they're doing.
local function buildEditorCmd(template, path)
	local quoted = "'" .. path:gsub("'", "'\\''") .. "'"
	local out, n = template:gsub("{file}", quoted)
	if n == 0 then
		out = template .. " " .. quoted
	end
	return out
end

local function sendSave(edit_id, content)
	if sendGMCP then
		sendGMCP("Editor.Save", yajl.to_string({ id = edit_id, content = content }))
	end
end

local function sendCancel(edit_id)
	if sendGMCP then
		sendGMCP("Editor.Cancel", yajl.to_string({ id = edit_id }))
	end
end

-- Wait for the editor to finish, then read the file back and dispatch
-- Save (mtime changed = user saved) or Cancel (mtime unchanged = closed
-- without saving). We poll at 200ms while the spawn handle is running
-- and switch to mtime polling at 2s for non-blocking openers (xdg-open).
-- 30-minute backstop overall.
local POLL_FAST = 0.2
local POLL_SLOW = 2.0
local DEADLINE_SECONDS = 1800

local function finishSession(edit_id)
	local sess = sessions[edit_id]
	if not sess then return end
	sessions[edit_id] = nil
	local newMtime = fileMtime(sess.path)
	local content = readWholeFile(sess.path)
	os.remove(sess.path)
	if content == nil then
		cecho("\n<red>[djangomoo]<reset> editor: could not read " .. sess.path .. "; cancelling edit\n")
		sendCancel(edit_id)
		return
	end
	if newMtime <= sess.startMtime then
		cecho("\n<DimGrey>[djangomoo]<reset> editor closed without saving; edit cancelled\n")
		sendCancel(edit_id)
		return
	end
	cecho(string.format("\n<DimGrey>[djangomoo]<reset> editor closed; sending %d bytes back to server\n", #content))
	sendSave(edit_id, content)
end

local function isHandleRunning(handle)
	if not handle or not handle.isRunning then return false end
	local ok, r = pcall(handle.isRunning)
	return ok and r
end

local function pollSession(edit_id)
	local sess = sessions[edit_id]
	if not sess then return end
	local elapsed = os.time() - sess.startTime
	if elapsed >= DEADLINE_SECONDS then
		cecho("\n<red>[djangomoo]<reset> editor session timed out after 30 minutes; finalising\n")
		finishSession(edit_id)
		return
	end
	if isHandleRunning(sess.handle) then
		tempTimer(POLL_FAST, function() pollSession(edit_id) end)
		return
	end
	-- Spawn exited. For non-blocking openers, the spawn returns immediately
	-- but the file may still be open in the GUI editor. Use mtime polling
	-- as the secondary signal: if mtime changed since start, treat as save
	-- and finish; otherwise keep watching at slow cadence.
	if fileMtime(sess.path) > sess.startMtime then
		finishSession(edit_id)
		return
	end
	tempTimer(POLL_SLOW, function() pollSession(edit_id) end)
end

-- Tell the server we support the Editor package, so it knows to hand
-- off open_editor() calls via GMCP instead of trying to draw the
-- prompt-toolkit TUI editor over a Mudlet TCP stream.
--
-- Idempotent and safe to call multiple times. The XML wires it to BOTH
-- `sysProtocolEnabled("GMCP")` (canonical, fires the moment IAC DO/WILL
-- completes) AND a sysConnectionEvent + 1.5s timer (defensive fallback
-- in case `sysProtocolEnabled` doesn't fire for some reason -- this is
-- belt-and-suspenders, not a real expectation).
local _advertised = false

function M.advertiseCapability(reason)
	if _advertised then
		cecho("\n<DimGrey>[djangomoo]<reset> Editor capability already advertised; skipping (" .. tostring(reason or "?") .. ")\n")
		return
	end
	if not sendGMCP then
		cecho("\n<red>[djangomoo]<reset> sendGMCP unavailable; cannot advertise Editor support\n")
		return
	end
	local ok, err = pcall(sendGMCP, "Core.Supports.Set", yajl.to_string({ "Editor 1" }))
	if ok then
		_advertised = true
		cecho("\n<DimGrey>[djangomoo]<reset> advertised GMCP <yellow>Editor 1<reset> to server (" .. tostring(reason or "?") .. ")\n")
	else
		cecho("\n<yellow>[djangomoo]<reset> Core.Supports.Set deferred (" .. tostring(reason or "?") .. " / " .. tostring(err) .. ")\n")
	end
end

-- Reset the latch on disconnect so a reconnect re-advertises.
function M.resetCapabilityLatch()
	_advertised = false
end

function M.onEditorStart()
	if not gmcp or not gmcp.Editor or not gmcp.Editor.Start then return end
	local payload = gmcp.Editor.Start
	local edit_id = payload.id
	if not edit_id then return end
	local content = payload.content or ""
	local content_type = payload.content_type or "text"
	local title = payload.title or "edit"

	local cfg = bridge_config.load()
	local cmdTemplate = cfg.editor_command or ""
	if cmdTemplate == "" then
		cecho("\n<red>[djangomoo]<reset> no editor configured. Run <yellow>dmsetup editor <command><reset> (use {file} as placeholder) and try again.\n")
		sendCancel(edit_id)
		return
	end

	local path = tempFilePath(edit_id, content_type)
	if not writeWholeFile(path, content) then
		cecho("\n<red>[djangomoo]<reset> could not write " .. path .. "; cancelling edit\n")
		sendCancel(edit_id)
		return
	end
	local startMtime = fileMtime(path)
	local cmd = buildEditorCmd(cmdTemplate, path)
	cecho(string.format("\n<DimGrey>[djangomoo]<reset> editing <yellow>%s<reset> via: %s\n", title, cmd))

	local function onLine(line)
		if line and line ~= "" then
			cecho("<DimGrey>[editor]<reset> " .. line)
			if not line:find("\n$") then cecho("\n") end
		end
	end
	local ok, handle
	if getOS() == "windows" then
		ok, handle = pcall(spawn, onLine, "cmd", "/c", cmd)
	else
		ok, handle = pcall(spawn, onLine, "/bin/sh", "-c", cmd)
	end
	if not ok or not handle then
		cecho("\n<red>[djangomoo]<reset> editor spawn failed: " .. tostring(handle) .. "\n")
		os.remove(path)
		sendCancel(edit_id)
		return
	end

	sessions[edit_id] = {
		path = path,
		handle = handle,
		startMtime = startMtime or 0,
		startTime = os.time(),
	}
	tempTimer(0.5, function() pollSession(edit_id) end)
end

return M
