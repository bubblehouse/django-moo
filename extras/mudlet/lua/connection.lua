-- Connection lifecycle for the djangomoo Mudlet package.
--
-- dmconnect launches sshelnet (downloading the binary on first use) and
-- then connects Mudlet to localhost on the configured local_port. The
-- spawned proxy is killed on disconnect or Mudlet exit so no orphaned
-- child process is left behind.

djangomoo = djangomoo or {}
djangomoo.connection = djangomoo.connection or {}

local M = djangomoo.connection
local bridge_config = djangomoo.bridge_config
local binary = djangomoo.binary
local setup = djangomoo.setup

local session_password = nil
-- sshelnet_handle is the table returned by Mudlet's spawn() — has
-- .send/.close/.isRunning methods. There's no exposed PID; we track
-- "is launched" via the handle itself.
local sshelnet_handle = nil

local function shellQuote(s)
	return "'" .. tostring(s):gsub("'", "'\\''") .. "'"
end

-- Spawn sshelnet via Mudlet 4.20.1's `spawn(callback, prog, ...args)`.
-- spawn calls `callback(line)` for every line of stdout/stderr from
-- the child process. The caller passes its own onLine to detect
-- readiness markers (e.g. sshelnet's "Listening on ..." log line).
local function spawnSshelnet(binPath, profileName, password, onLine)
	local ok, handleOrErr
	if getOS() == "windows" then
		local home = os.getenv("USERPROFILE") or os.getenv("HOME") or "."
		local wrapper = home .. "/.djangomoo-sshelnet-launch.cmd"
		local f = io.open(wrapper, "w")
		if not f then
			cecho("\n<red>[djangomoo]<reset> could not write Windows launcher\n")
			return nil
		end
		f:write("@echo off\r\n")
		if password and password ~= "" then
			f:write("set SSHELNET_PASSWORD=" .. password .. "\r\n")
		end
		f:write('"' .. binPath .. '" connect ' .. profileName .. "\r\n")
		f:close()
		ok, handleOrErr = pcall(spawn, onLine, wrapper)
	else
		local cmd = ""
		if password and password ~= "" then
			cmd = "SSHELNET_PASSWORD=" .. shellQuote(password) .. " "
		end
		cmd = cmd .. shellQuote(binPath) .. " connect " .. shellQuote(profileName)
		ok, handleOrErr = pcall(spawn, onLine, "/bin/sh", "-c", cmd)
	end
	if not ok then
		cecho("\n<red>[djangomoo]<reset> spawn failed: " .. tostring(handleOrErr) .. "\n")
		return nil
	end
	return handleOrErr
end

-- Mudlet's spawn handle exposes .close() which only closes stdin.
-- sshelnet doesn't read stdin in connect mode, so that's a no-op.
-- The reliable way to terminate the proxy is pkill against its
-- command-line. We match on the specific profile name so we don't
-- nuke unrelated sshelnet processes the user may have started by
-- hand. This also picks up orphans from previous Mudlet sessions
-- whose spawn handles are gone.
local function killSshelnet()
	if sshelnet_handle and sshelnet_handle.close then
		pcall(sshelnet_handle.close)
	end
	sshelnet_handle = nil
	local profileName = setup.sshelnetProfileName()
	if getOS() == "windows" then
		os.execute("taskkill /F /FI \"WINDOWTITLE eq sshelnet\" >nul 2>&1")
	else
		os.execute("pkill -f " .. shellQuote("sshelnet connect " .. profileName) .. " 2>/dev/null")
	end
end

local function continueConnect(cfg, password)
	binary.ensureBinaryAsync(function(binPath, err)
		if err then
			cecho("\n<red>[djangomoo]<reset> sshelnet binary unavailable: " .. tostring(err) .. "\n")
			return
		end
		-- Regenerate the sshelnet YAML profile on every connect. Cheap
		-- and idempotent; guarantees the profile exists at launch time
		-- even if the user configured before this auto-write was added,
		-- or hand-edited the file in between.
		if not setup.writeSshelnet() then
			return
		end
		local profileName = setup.sshelnetProfileName()

		-- Wait for sshelnet to log "Listening on ..." before initiating
		-- Mudlet's TCP connect. Mudlet's Lua doesn't bundle LuaSocket so
		-- we can't probe the port directly; instead we watch the proxy's
		-- merged stdout/stderr (Mudlet's spawn pipes both into onLine).
		local connected = false
		local timeoutTimer

		local function onReady()
			if connected then return end
			connected = true
			if timeoutTimer then
				killTimer(timeoutTimer)
				timeoutTimer = nil
			end
			cecho(string.format("\n<DimGrey>[djangomoo]<reset> connecting to 127.0.0.1:%d via sshelnet\n", cfg.local_port))
			connectToServer("127.0.0.1", cfg.local_port)
		end

		local function onLine(line)
			if not line or line == "" then return end
			cecho("<DimGrey>[sshelnet]<reset> " .. line)
			if not line:find("\n$") then cecho("\n") end
			if not connected and line:find("Listening on") then
				onReady()
			elseif line:find("address already in use") then
				cecho("<yellow>[djangomoo]<reset> port " .. cfg.local_port
					.. " is in use. another sshelnet may be running. run "
					.. "<yellow>dmkill<reset> to clean up, then <yellow>dmconnect<reset> again.\n")
			end
		end

		sshelnet_handle = spawnSshelnet(binPath, profileName, password, onLine)
		if not sshelnet_handle then
			cecho("\n<red>[djangomoo]<reset> failed to launch sshelnet\n")
			return
		end
		cecho("<DimGrey>[djangomoo]<reset> sshelnet launched; waiting for \"Listening on ...\" log line\n")

		-- Fallback: if sshelnet hasn't logged readiness within 5 seconds,
		-- give up. Avoids hanging forever when sshelnet errors silently.
		timeoutTimer = tempTimer(5, function()
			if not connected then
				cecho("\n<red>[djangomoo]<reset> sshelnet did not bind within 5s; giving up\n")
				killSshelnet()
			end
		end)
	end)
end

-- Use a permanent package-registered alias toggled active/inactive by name
-- (defined in djangomoo.xml as "djangomoo_password_capture"). tempAlias has
-- proven unreliable across Mudlet versions, but enableAlias/disableAlias on
-- a package-installed alias is rock-solid.
--
-- The alias must NOT be enabled inside the same input-processing tick that
-- runs `dmconnect` -- if it were, Mudlet would immediately match `^(.+)$`
-- against the literal `dmconnect` text and capture that as the password.
-- tempTimer(0, ...) defers enableAlias to the next event-loop tick so the
-- prompt only matches the user's NEXT typed line.
local function promptPassword(onPassword)
	cecho("\n<DimGrey>[djangomoo]<reset> SSH password (single line; appears in window but not sent to MUD).\n")
	cecho("<DimGrey>[djangomoo]<reset> If your next line isn't captured, run <yellow>dmpassword <your-pw><reset> instead.\n")
	cecho("<DimGrey>[djangomoo]<reset> password> ")
	djangomoo._pwcb = onPassword
	tempTimer(0, function() enableAlias("djangomoo_password_capture") end)
end

function M.onPasswordCapture(pw)
	disableAlias("djangomoo_password_capture")
	local cb = djangomoo._pwcb
	djangomoo._pwcb = nil
	session_password = pw
	cecho("\n<DimGrey>[djangomoo]<reset> password received; continuing...\n")
	if cb then cb(pw) end
end

function M.setPassword(pw)
	session_password = pw
end

function M.clearPassword()
	session_password = nil
	cecho("\n<DimGrey>[djangomoo]<reset> cached password cleared.\n")
end

function M.dmpassword(pw)
	if not pw or pw == "" then
		M.clearPassword()
		return
	end
	M.setPassword(pw)
	cecho("\n<DimGrey>[djangomoo]<reset> password cached for this Mudlet session.\n")
end

function M.dmconnect()
	local cfg = bridge_config.load()
	local ok, missing = bridge_config.isComplete(cfg)
	if not ok then
		cecho(string.format("\n<red>[djangomoo]<reset> setup incomplete (missing %s). run <yellow>dmsetup help<reset>.\n", missing))
		return
	end
	-- Clear any orphan sshelnet processes from previous Mudlet sessions
	-- before launching a fresh one. This handles the common case where
	-- a prior dmconnect succeeded in binding the local port but Mudlet
	-- was reloaded / the connection failed to take, leaving sshelnet
	-- bound to 127.0.0.1:<local_port> with no Lua reference to it.
	killSshelnet()
	if cfg.auth_method == "password" and not session_password then
		promptPassword(function(pw)
			continueConnect(cfg, pw)
		end)
		return
	end
	continueConnect(cfg, session_password)
end

function M.dmkill()
	cecho("\n<DimGrey>[djangomoo]<reset> killing any sshelnet processes for this profile...\n")
	killSshelnet()
end

function M.dmstatus()
	local cfg = bridge_config.load()
	local installed = binary.installedVersion() or "(none)"
	local running = "no"
	if sshelnet_handle and sshelnet_handle.isRunning then
		local ok, r = pcall(sshelnet_handle.isRunning)
		if ok and r then running = "yes" end
	end
	cecho(string.format([[

<DimGrey>[djangomoo status]<reset>
  sshelnet binary  = %s
  installed version = %s
  pinned version    = %s
  sshelnet running  = %s
  password cached   = %s
  config host       = %s
  config local_port = %s
]],
		binary.path(), installed, binary.pinnedVersion(),
		running,
		session_password and "yes" or "no",
		tostring(cfg.host), tostring(cfg.local_port)))
end

function M.onDisconnect()
	killSshelnet()
	if djangomoo and djangomoo.editor and djangomoo.editor.resetCapabilityLatch then
		djangomoo.editor.resetCapabilityLatch()
	end
end

function M.onExit()
	killSshelnet()
end

function M.dmupgrade()
	binary.upgradeAsync(function(_, err)
		if err then
			cecho("\n<red>[djangomoo]<reset> upgrade failed: " .. tostring(err) .. "\n")
		end
	end)
end

return M
