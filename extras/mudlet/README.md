# DjangoMOO Mudlet Package

End-to-end Mudlet integration for [DjangoMOO](https://gitlab.com/bubblehouse/django-moo)
servers. The package handles three things:

- **Managed sshelnet launcher.** Mudlet has no native SSH support; DjangoMOO
  speaks SSH. This package downloads the right
  [sshelnet](https://gitlab.com/bubblehouse/sshelnet) release binary on first
  use, caches it under your Mudlet profile dir, and runs it as a child process
  during the connection. Mudlet itself talks plain TCP to `127.0.0.1` and
  sshelnet bridges the rest.
- **Setup wizard (`dmsetup`)** that captures host / port / username / auth
  method and writes the matching `~/.config/sshelnet/config.yaml` profile.
- **Generic-mapper bridge.** Subscribes to `gmcp.Room.Info` and feeds the
  payload into Mudlet's bundled "generic mapper" (`map.prompt.room`,
  `map.prompt.exits`, `onNewRoom`).

## Installation

1. Open *Settings -> Package Manager* in Mudlet.
2. Click *Install*, then select `djangomoo.mpackage`.
3. Install Mudlet's bundled generic-mapper package the same way -- click
   *Install* and pick `generic_mapper.mpackage` from your Mudlet
   install dir. On macOS that's
   `/Applications/mudlet.app/Contents/Resources/mudlet-lua/lua/generic-mapper/generic_mapper.mpackage`.
   Without it, the bridge will print a one-time warning on the first
   `Room.Info` and mapping will be disabled.
4. Configure your Mudlet profile to point at `127.0.0.1:<local_port>` (the
   default `local_port` is `8023`). Turn **autoconnect off** -- the package
   handles connection via `dmconnect`.

## Setup

Run the setup wizard once per profile:

```text
dmsetup host moo.example.com
dmsetup port 8022
dmsetup username yourname
dmsetup local-port 8023
dmsetup auth password         # or "key" / "agent"
dmsetup key-file ~/.ssh/id_ed25519   # only for auth=key
dmsetup show
```

Each command writes the new value and (for the connection-relevant fields)
regenerates the corresponding sshelnet YAML profile at
`~/.config/sshelnet/config.yaml` under the name `mudlet-<profilename>`.

`dmsetup` (no args) prints usage; `dmsetup help` does the same.

## Connecting

```text
dmconnect
```

Behavior:

1. On first use, downloads the pinned sshelnet binary for your platform from
   GitLab releases (cached under `<Mudlet profile dir>/sshelnet/`).
2. If `auth_method` is `password` and there's no cached password yet, prompts
   for it once. The next line you type is captured as the password and used
   only for this Mudlet session -- never written to disk.
3. Spawns sshelnet with `SSHELNET_PASSWORD` set in its environment, then
   connects Mudlet to `127.0.0.1:<local_port>`.

Reconnecting in the same Mudlet session reuses the cached password.
Disconnecting (or quitting Mudlet) kills the sshelnet child process.

## Mapping

The bridge feeds GMCP `Room.Info` events into Mudlet's generic mapper, but
the mapper does not start drawing rooms until you turn it on. After you've
connected and the first `Room.Info` has arrived (you'll see the prompt),
run:

```text
start mapping <area name>
```

For example: `start mapping moo`. This sets `map.mapping = true`, creates
the first room from the current `Room.Info`, and from then on every move
adds a room and links it to its predecessor. `stop mapping` turns it
back off.

If the bridge sees that mapping is off when a `Room.Info` arrives, it
prints a one-time hint pointing at this command. Open the map view with
*View -> Show map* (or `Alt+M`).

## Other commands

| Command      | What it does                                                |
|--------------|-------------------------------------------------------------|
| `dmstatus`   | Show binary path, installed version, running state, config  |
| `dmkill`     | `pkill` any sshelnet process for this profile (orphan cleanup) |
| `dmupgrade`  | Fetch and install the latest sshelnet release from GitLab   |

`dmconnect` always runs `dmkill` first, so orphans from previous Mudlet
sessions are cleaned up automatically.

The package checks GitLab for newer sshelnet versions at most once a week and
nudges you via a yellow message in the main window when there's an upgrade.

## External editor for `@edit`

The bridge advertises GMCP `Editor` support via `Core.Supports.Set`, so
when you run `@edit verb_name on $obj` (or any other verb that calls
`open_editor()` server-side -- `@describe`, `@send`, `@reply`, `@gripe`,
`@forward`, `@edit` for notes), the server sends the content to your
client over GMCP and the bridge launches your **local** editor on it.
When you save and close, the new content is sent back over GMCP and the
server applies it. The prompt-toolkit TUI editor that doesn't render
correctly in Mudlet is bypassed entirely.

Default editor commands per OS (use `{file}` as the path placeholder):

| OS      | Default                | Notes                                                 |
|---------|------------------------|-------------------------------------------------------|
| macOS   | `open -W -t {file}`    | TextEdit / OS-default app, blocks until window closes |
| Linux   | `xdg-open {file}`      | Doesn't block; bridge falls back to mtime polling     |
| Windows | `notepad {file}`       | Blocks naturally                                      |

Override with:

```text
dmsetup editor code --wait {file}        # VS Code, blocking
dmsetup editor subl --wait {file}        # Sublime Text, blocking
dmsetup editor open -W -a Atom {file}    # Force a specific Mac app
```

Closing the editor without saving cancels the edit. Bridge sends
`Editor.Cancel` and the server discards the pending callback.

## Requirements

- **sshelnet >= v1.0.0** (the version with `SSHELNET_PASSWORD` env-var
  support). The package downloads this automatically.
- Mudlet 4.10 or newer (uses `runShellCommand`, `unzipAsync`, `getHTTP`).

## Notes on the package icon

The package ships an `icon.png` and `icon = [[icon.png]]` in `config.lua`,
but Mudlet's Package Manager only renders package icons for packages
installed from its **central repository** (`mpkg.packages.json`). Locally-
installed `.mpackage` files always show the blank/default placeholder. The
icon stays bundled for forward-compatibility if we later publish to
Mudlet's repository.

## Source layout

| Path                     | Purpose                                              |
|--------------------------|------------------------------------------------------|
| `config.lua`             | Mudlet package metadata (also pins sshelnet version) |
| `djangomoo.xml`          | Aliases + event-handler scripts                      |
| `lua/bridge_config.lua`  | Read/write of the bridge config table                |
| `lua/binary.lua`         | sshelnet download / version pinning / upgrade        |
| `lua/connection.lua`     | `dmconnect` / `dmstatus` / disconnect cleanup        |
| `lua/editor.lua`         | GMCP `Editor.Start` handler — external-editor handoff |
| `lua/mapper.lua`         | `gmcp.Room.Info` -> generic-mapper bridge            |
| `lua/setup.lua`          | `dmsetup` command surface                            |
| `unicow.jpg`             | Package icon (project mascot)                        |
| `build.sh`               | Zips the above into `djangomoo.mpackage`             |

## Rebuilding

```sh
./build.sh
```

Bump `version` in `config.lua` if you ship behavioral changes. Bump
`sshelnet_pinned_version` to ship a new bundled sshelnet baseline.

## Other clients

There is no universal mapping protocol that "just works" across MUD clients.
MUSHclient, TinTin++, ZMUD/CMUD, and BlowTorch all need their own equivalent
shim. The Room.Info payload shape documented in
[`docs/source/how-to/accessibility.md`](../../docs/source/how-to/accessibility.md)
is the contract -- pick whatever scripting hook your client provides and copy
the fields into its mapper state.
