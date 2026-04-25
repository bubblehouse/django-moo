-- sshelnet binary bootstrapper.
--
-- Downloads the right release binary from gitlab.com/bubblehouse/sshelnet
-- on first use, caches it under getMudletHomeDir() .. "/sshelnet/", and
-- offers a throttled latest-version check via dmupgrade.
--
-- VERSION file is the runtime source of truth: once a binary is installed,
-- the package keeps using it until dmupgrade swaps it. The pinned version
-- in config.lua only matters on first install (no VERSION file yet).

djangomoo = djangomoo or {}
djangomoo.binary = djangomoo.binary or {}

local M = djangomoo.binary

local CACHE_DIR = getMudletHomeDir() .. "/sshelnet"
local VERSION_FILE = CACHE_DIR .. "/VERSION"
local LAST_CHECK_FILE = CACHE_DIR .. "/.last_update_check"
local UPDATE_CHECK_INTERVAL = 7 * 24 * 60 * 60
-- Use the numeric project ID instead of the URL-encoded path. Mudlet's
-- QUrl::fromUserInput normalizes URLs and decodes %2F back to /, which
-- breaks the GitLab API's namespace/project encoding ("bubblehouse/sshelnet"
-- gets read as a different path entirely). Numeric IDs sidestep that.
local PROJECT_ID = "81449522"
local PROJECT_API = "https://gitlab.com/api/v4/projects/" .. PROJECT_ID
local LATEST_RELEASE_API = PROJECT_API .. "/releases/permalink/latest"

local pinned_version = "v1.0.0"

local function fileExists(path)
	local f = io.open(path, "r")
	if f then
		f:close()
		return true
	end
	return false
end

local function readFile(path)
	local f = io.open(path, "r")
	if not f then return nil end
	local s = f:read("*a")
	f:close()
	return s
end

local function writeFile(path, content)
	local f, err = io.open(path, "w")
	if not f then return false, err end
	f:write(content)
	f:close()
	return true
end

local function ensureCacheDir()
	if fileExists(CACHE_DIR) then return end
	if lfs and lfs.mkdir then
		lfs.mkdir(CACHE_DIR)
	else
		os.execute("mkdir -p '" .. CACHE_DIR .. "'")
	end
end

local function platformInfo()
	local osn = getOS()
	local os_str, ext
	if osn == "mac" then
		os_str, ext = "darwin", ""
	elseif osn == "windows" then
		os_str, ext = "windows", ".exe"
	else
		os_str, ext = "linux", ""
	end

	local archn = "amd64"
	if osn == "windows" then
		local proc = os.getenv("PROCESSOR_ARCHITECTURE") or ""
		if proc:upper():find("ARM64") then archn = "arm64" end
	else
		local p = io.popen("uname -m 2>/dev/null")
		if p then
			local result = (p:read("*l") or ""):lower()
			p:close()
			if result == "aarch64" or result == "arm64" then
				archn = "arm64"
			elseif result == "x86_64" or result == "amd64" then
				archn = "amd64"
			end
		end
	end
	return os_str, archn, ext
end

local function binaryPath()
	local _, _, ext = platformInfo()
	return CACHE_DIR .. "/sshelnet" .. ext
end

function M.path()
	return binaryPath()
end

function M.installedVersion()
	local v = readFile(VERSION_FILE)
	if v then v = v:gsub("%s+$", "") end
	return v
end

function M.setPinnedVersion(v)
	if v and v ~= "" then pinned_version = v end
end

function M.pinnedVersion()
	return pinned_version
end

local function findAssetURL(release_json)
	if not release_json or not release_json.assets or not release_json.assets.links then
		return nil
	end
	local os_str, archn = platformInfo()
	local needle = os_str .. "_" .. archn
	for _, link in ipairs(release_json.assets.links) do
		if link.name and link.url and link.name:find(needle, 1, true) and link.name:find("%.zip$") then
			return link.url, link.name
		end
	end
	return nil
end

local function fetchReleaseJSON(url, onDone)
	cecho("\n<DimGrey>[djangomoo]<reset> GET " .. url .. "\n")
	local handlerDone, handlerErr
	handlerDone = registerAnonymousEventHandler("sysGetHttpDone", function(_, fetchedUrl, response)
		killAnonymousEventHandler(handlerDone)
		if handlerErr then killAnonymousEventHandler(handlerErr) end
		cecho(string.format("<DimGrey>[djangomoo]<reset> HTTP done (%d bytes)\n", #(response or "")))
		local ok, parsed = pcall(yajl.to_value, response)
		if not ok then
			onDone(nil, "yajl.to_value failed: " .. tostring(parsed))
			return
		end
		if type(parsed) ~= "table" then
			onDone(nil, "release JSON did not parse to a table (got " .. type(parsed) .. ")")
			return
		end
		onDone(parsed, nil)
	end, true)
	handlerErr = registerAnonymousEventHandler("sysGetHttpError", function(_, errMsg, fetchedUrl)
		if handlerDone then killAnonymousEventHandler(handlerDone) end
		killAnonymousEventHandler(handlerErr)
		onDone(nil, "HTTP error: " .. tostring(errMsg))
	end, true)
	getHTTP(url)
end

local function downloadAndInstall(release_json, version, onDone)
	ensureCacheDir()
	local url, name = findAssetURL(release_json)
	if not url then
		local os_str, archn = platformInfo()
		onDone(false, string.format("no sshelnet asset matches platform %s_%s in release %s", os_str, archn, version))
		return
	end
	cecho(string.format("<DimGrey>[djangomoo]<reset> matched asset %s\n", name))
	local zipPath = CACHE_DIR .. "/" .. name
	local handlerDone, handlerErr, handlerUnzip, handlerUnzipErr

	handlerDone = registerAnonymousEventHandler("sysDownloadDone", function(_, filename)
		if filename ~= zipPath then return end
		killAnonymousEventHandler(handlerDone)
		if handlerErr then killAnonymousEventHandler(handlerErr) end
		cecho("<DimGrey>[djangomoo]<reset> download complete; extracting...\n")

		handlerUnzip = registerAnonymousEventHandler("sysUnzipDone", function(_, zipFile)
			if zipFile ~= zipPath then return end
			killAnonymousEventHandler(handlerUnzip)
			if handlerUnzipErr then killAnonymousEventHandler(handlerUnzipErr) end
			cecho("<DimGrey>[djangomoo]<reset> extraction complete\n")
			if getOS() ~= "windows" then
				-- Mudlet 4.20.1's process-launch primitive is `spawn`,
				-- not `runShellCommand`. spawn(cb, prog, ...args).
				local ok, err = pcall(spawn, function() end, "chmod", "+x", binaryPath())
				if not ok then
					cecho("<DimGrey>[djangomoo]<reset> chmod failed: " .. tostring(err) .. "\n")
				end
			end
			writeFile(VERSION_FILE, version .. "\n")
			os.remove(zipPath)
			onDone(true, nil)
		end, true)

		handlerUnzipErr = registerAnonymousEventHandler("sysUnzipError", function(_, zipFile)
			if zipFile ~= zipPath then return end
			killAnonymousEventHandler(handlerUnzipErr)
			if handlerUnzip then killAnonymousEventHandler(handlerUnzip) end
			onDone(false, "unzip failed for " .. tostring(zipFile))
		end, true)

		unzipAsync(zipPath, CACHE_DIR)
	end, true)

	handlerErr = registerAnonymousEventHandler("sysDownloadError", function(_, errMsg, filename)
		if filename ~= zipPath then return end
		killAnonymousEventHandler(handlerErr)
		if handlerDone then killAnonymousEventHandler(handlerDone) end
		onDone(false, "download failed: " .. tostring(errMsg))
	end, true)

	cecho(string.format("<DimGrey>[djangomoo]<reset> downloading %s ...\n", url))
	downloadFile(zipPath, url)
end

function M.ensureBinaryAsync(onDone)
	ensureCacheDir()
	if fileExists(binaryPath()) and M.installedVersion() then
		onDone(binaryPath(), nil)
		return
	end
	cecho("\n<DimGrey>[djangomoo]<reset> downloading sshelnet " .. pinned_version .. "...\n")
	local target = pinned_version
	local url
	if target == "latest" then
		url = LATEST_RELEASE_API
	else
		url = PROJECT_API .. "/releases/" .. target
	end
	fetchReleaseJSON(url, function(parsed, err)
		if err then onDone(nil, err); return end
		downloadAndInstall(parsed, target, function(ok, errMsg)
			if not ok then onDone(nil, errMsg); return end
			cecho("\n<DimGrey>[djangomoo]<reset> sshelnet " .. target .. " ready.\n")
			onDone(binaryPath(), nil)
		end)
	end)
end

function M.upgradeAsync(onDone)
	cecho("\n<DimGrey>[djangomoo]<reset> checking for the latest sshelnet...\n")
	fetchReleaseJSON(LATEST_RELEASE_API, function(parsed, err)
		if err then onDone(false, err); return end
		local tag = parsed and parsed.tag_name
		if not tag then onDone(false, "no tag_name in release JSON"); return end
		if tag == M.installedVersion() then
			cecho("\n<DimGrey>[djangomoo]<reset> already on latest (" .. tag .. ").\n")
			onDone(true, nil)
			return
		end
		cecho("\n<DimGrey>[djangomoo]<reset> upgrading to " .. tag .. "...\n")
		downloadAndInstall(parsed, tag, function(ok, errMsg)
			if ok then
				cecho("\n<DimGrey>[djangomoo]<reset> sshelnet upgraded to " .. tag .. ".\n")
			end
			onDone(ok, errMsg)
		end)
	end)
end

function M.checkForUpdate()
	local now = os.time()
	local last = tonumber(readFile(LAST_CHECK_FILE) or "0") or 0
	if now - last < UPDATE_CHECK_INTERVAL then return end
	writeFile(LAST_CHECK_FILE, tostring(now))

	fetchReleaseJSON(LATEST_RELEASE_API, function(parsed, err)
		if err or not parsed or not parsed.tag_name then return end
		local installed = M.installedVersion()
		if installed and parsed.tag_name ~= installed then
			cecho("\n<DimGrey>[djangomoo]<reset> sshelnet "
				.. parsed.tag_name .. " is available (you have "
				.. installed .. "). Run <yellow>dmupgrade</yellow> to update.\n")
		end
	end)
end

return M
