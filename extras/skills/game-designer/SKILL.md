---
name: game-designer
description: Design and build themed multi-room environments in DjangoMOO via SSH wizard commands. Triggered by: "build a MOO environment", "create rooms for X", "design a location based on Y", "add NPCs for Z", "write a test verb for", "set up a MOO area", "implement a themed space in MOO".
compatibility: DjangoMOO project (django-moo). Requires a wizard SSH session.
---

# Game Designer Skill

You are designing and building a themed multi-room environment in DjangoMOO. Follow this 5-phase workflow.

## Phase 1: Research

Before writing any commands, research the theme thoroughly:

- Physical layout: How many rooms? What are their names and spatial relationships?
- Objects: What items are present? Which are interactive vs. decorative?
- Characters: Who lives here? What do they say or do?
- Signature interactions: What verbs make this space feel alive? (sit, drink, order, throw, play)
- Atmosphere: What descriptions capture the feel of each room?

Use web research for real-world locations. Aim for specificity — generic descriptions produce generic spaces.

## Phase 2: Design - Generate YAML Environment File

Create a YAML environment file with this structure:

```yaml
metadata:
  name: "Environment Name"
  description: "Brief description"
  author: "game-designer"
  version: "1.0"
  base_parent: "$thing"    # Default parent for objects
  npc_parent: "$player"     # Default parent for NPCs
  use_hash_suffix: true     # Enable hash suffixes for testing

rooms:
  - name: "Room Name"
    description: "Detailed room description..."
    exits:
      - direction: north
        to: "Other Room"
      - direction: south
        to: "External Room"
        reverse: north  # Tunnel back to existing room

objects:
  "Room Name":
    - name: "object name"
      description: "Object description..."
      aliases: ["alias1", "alias2"]
      obvious: true  # Appears in room listing when players look (default: false)
      quantity: 4  # Create 4 identical objects

npcs:
  - name: "NPC Name"
    description: "NPC description..."
    aliases: ["alias"]
    room: "Room Name"

verbs:
  - verb: "verb_name"
    object: "object name"
    room: "Room Name"  # For disambiguation
    code: |
      from moo.sdk import context
      # Verb implementation...
```

When creating descriptions, review the `references/room-description-principles.md` reference for guidelines on effective writing. Key principle: room descriptions should be atmospheric, not inventories. The `obvious` object listing handles enumeration — descriptions handle character and orientation.

**For each object, decide: `obvious: true` or `obvious: false`?**

- `obvious: true` — the object appears in the room listing when players `look`. Use for dominant furniture, interactive focal points, major props, anything a person would immediately notice walking in.
- `obvious: false` (default) — hidden from the listing, discovered by examining other objects or through narrative hints. Use for small details, easter eggs, items found by searching.

Objects marked `obvious: true` should be mentioned in the room description. Non-obvious objects don't need to be — though a description can hint at them as flavor or reward for curiosity.

**Key sections:**

1. **metadata**: Environment info, parent defaults, hash mode
   - `use_hash_suffix: true` — Testing/development mode (adds `[abc123]` to names)
   - `use_hash_suffix: false` — Production mode (clean names)
2. **rooms**: List of room definitions with inline exits
3. **objects**: Dict mapping room names to object lists (use `quantity` for duplicates)
4. **npcs**: List of NPC definitions with starting rooms
5. **verbs**: List of verb definitions with multi-line code blocks
6. **test**: (Optional) Explicit test expectations, or omit for auto-generation

**Hash Mode Usage:**
- **During development**: `use_hash_suffix: true` allows repeated builds without cleanup
- **For production**: `use_hash_suffix: false` produces clean professional names
- **CLI override**: `--hash` or `--no-hash` flags override YAML setting

**Save to**: `extras/skills/game-designer/environments/<name>.yaml`

**Example**: See `environments/moes-tavern.yaml` for a complete working example

## Phase 3: Review YAML (User Approval Required)

After generating the YAML file:

1. **Show the file path** to the user: `extras/skills/game-designer/environments/<name>.yaml`
2. **Summarize what will be created**:
   - X rooms with Y exits
   - Z objects across N rooms
   - M NPCs
   - P interactive verbs
3. **Ask the user to review** the YAML file
4. **Wait for explicit approval** before proceeding to Phase 4
5. **Allow edits**: User can manually edit the YAML if needed

This review step prevents committing to a multi-minute build process without user validation of the content.

**Do not proceed to Phase 4 until the user approves the YAML file.**

## Phase 4: Build - Invoke Build Script

After user approval, execute the build script **in the background** — builds take 3-4 minutes and must not block the conversation:

```bash
python extras/skills/game-designer/tools/build_from_yaml.py \
    extras/skills/game-designer/environments/<name>.yaml
```

**Options:**
- `--dry-run`: Parse YAML without connecting to MOO
- `--no-test`: Skip test verb creation
- `--hash`: Force hash suffix mode (override YAML setting)
- `--no-hash`: Force clean name mode (override YAML setting)
- `--host HOST --port PORT`: Custom SSH connection

**For local development**, a DB refresh and server restart before each build ensures a clean state. For production deploys, just run the build against the live server. If the server is unresponsive mid-build, you can restart it yourself with `docker compose restart webapp celery` — but tell the user first.

**Build process:**
1. **Phase 1: Rooms and exits**: Creates rooms in void, digs exits, tunnels back
2. **Phase 2: Objects**: Creates objects in void, describes, adds aliases, moves to rooms
3. **Phase 3: NPCs**: Creates NPCs, describes, adds aliases, moves to rooms
4. **Phase 4: Verbs**: Attaches verbs to objects/NPCs using resolved references
5. **Phase 5: Test verb**: Generates test code, places on `$programmer`, runs verification

**Do not use `@reload`** — it creates duplicate verbs on a freshly-bootstrapped DB. The user handles verb state by refreshing the DB before each build.

**Build time**: ~3-4 minutes for typical environments (5 rooms, 30+ objects). The build script uses automation mode (PREFIX/SUFFIX delimiters + QUIET mode) automatically — each command takes ~1.1s instead of the old ~7.5s.

**What you'll see:**
- Progress messages for each phase (stderr)
- Real-time command execution trace (stdout)
- Object IDs captured (e.g., `#45: bar stool`)
- Warnings for any unresolved references
- Final test results with pass/fail counts

**Monitor output** for errors. The script will print progress and warnings. Each phase completes before moving to the next.

## Phase 5: Verify - Auto-Generated Test Verb

The test verb is automatically generated and run by `build_from_yaml.py`.

**Test verb name**:
- With hash: `test-<env-name>-<hash>` (e.g., `test-moes-tavern-abc123`)
- Without hash: `test-<env-name>` (e.g., `test-moes-tavern`)

**Test verb verifies**:
- All rooms exist and are accessible
- All objects are in correct rooms
- All NPCs are present
- All verbs are attached to correct objects

**Manual re-run**:
```
test-<env-name>-<hash>
```

The test verb name is printed at the end of the build output.

**Custom tests**: You can still create custom test verbs if needed, but auto-generation covers standard verification cases.

## Best Practices & Tips

Based on validated builds:

### YAML Authoring

1. **Use `quantity` for duplicates**: Instead of repeating object definitions, use `quantity: 4` to create multiple identical objects
2. **Organize by room**: Group objects under their destination rooms for clarity
3. **Mark obvious objects explicitly**: Every object that should appear in the room listing needs `obvious: true` — the default is `false`. Think: what would someone notice immediately walking in?
4. **Write descriptions for atmosphere, not inventory**: `obvious` objects appear in the room listing automatically. Room descriptions should orient and evoke, not enumerate. A description that reads like a bullet list means too many objects are being named.
5. **Hash mode for testing**: Set `use_hash_suffix: true` during development, `false` for production
6. **Comment liberally**: YAML supports comments - explain non-obvious design decisions

### Build Process

1. **Always run `--dry-run` first**: Validate YAML syntax before committing to a 3-4 minute build
2. **Local development**: DB refresh + server restart before each build keeps the state clean. Production deploys skip this.
3. **One build at a time**: Don't run multiple builds simultaneously (Wizard moves between rooms)
4. **Run in background**: Use `python ... > /tmp/build.log 2>&1 &` and monitor the log every 2 minutes
5. **Monitor output**: Watch for `WARNING: could not get ID` (off-by-one) and traceback lines
6. **Do not use `@reload`**: Creates duplicate verbs — user manages verb state via DB refresh

### Multiline Descriptions

YAML block scalars (`|` or `>`) produce Python strings with literal `\n` characters. The `describe()` function in `build_from_yaml.py` handles this correctly — it escapes `\n` as `\\n` before sending via SSH, and `at_describe.py` unescapes them when storing. **This means multiline descriptions work fine in YAML.** Write them as block scalars freely.

### RestrictedPython Gotchas in Generated Verb Code

The test verb (and any generated verb code) runs inside the RestrictedPython sandbox. Subscript augmented assignment is blocked:

```python
# BLOCKED — RestrictedPython compilation failure (silent: code.code = None)
results["passed"] += 1

# CORRECT — use plain variables
passed += 1
failed += 1
```

If a generated verb silently fails with `TypeError: exec() arg 1 must be a string, bytes or code object`, it means RestrictedPython couldn't compile it. Check for any `dict["key"] += value` patterns and replace with plain variables.

### Performance

- Each command takes ~1.1s (0.1s execution + 1s settle delay) vs the old ~7.5s
- Typical 5-room environment: ~3-4 minutes (down from 15-20 minutes)
- Uses clean `@alias` commands instead of verbose `@eval` calls
- Hash mode adds minimal overhead (suffix generation is fast)

### Troubleshooting

- **"No such object" errors**: Check room names match exactly (case-sensitive)
- **Ambiguous object errors**: Use `room` context in verb definitions
- **Test verb failures**: Verify hash is included in object names when hash mode enabled
- **`TypeError: exec() arg 1 must be a string, bytes or code object`**: RestrictedPython compilation failure — check for `dict["key"] += value` patterns in generated code
- **SSH disconnects mid-build**: Run `docker compose restart webapp celery` to restore, then re-run the build script (tell the user first)
- **`WARNING: could not get ID` in build log**: The off-by-one bug — likely a description with unescaped newlines being sent as a split command. All descriptions are now correctly escaped; this should not recur.

## Available Build Commands

The following specialized verbs are available for world building:

### `@alias` verb

Add aliases to objects without using `@eval`:

```
@alias #N as "alias"
@alias "object name" as "alias"
```

**Examples:**
- `@alias #45 as "stool"`
- `@alias "pool table" as "table"`
- `@alias "jukebox" as "juke"`

The verb supports global lookup (can reference objects anywhere by name or #N ID). Permissions are enforced by the object model — you can only add aliases to objects you own or have appropriate permissions for.

**Implementation:** `moo/bootstrap/default_verbs/player/at_alias.py`

## Build Automation

All environments are built using the generic `build_from_yaml.py` script. This YAML-driven approach provides:

**Benefits:**
- **Repeatable builds**: Content in YAML, logic in Python
- **Version control**: YAML diffs show actual content changes
- **No code knowledge needed**: Edit YAML directly, no Python required
- **Hash mode**: Optional hash suffixes for testing (allows repeated builds)
- **Automated testing**: Test verbs auto-generated from YAML structure
- **Improved efficiency**: ~13% reduction in commands using `@alias` verb instead of `@eval`

**Scripts:**
- `build_from_yaml.py` — Generic YAML-driven builder (✅ tested and validated)
- `build_moes_tavern.py` — Original monolithic script (reference only)

**Example environment**: `environments/moes-tavern.yaml` (complete 5-room Simpsons tavern)

**Validation**: Both scripts have been tested side-by-side and produce equivalent environments. The YAML approach uses 48 `@alias` commands vs 132 `@eval` alias commands in the original, resulting in cleaner output and faster execution.

See `references/build-automation.md` for YAML schema details and advanced patterns.

## Complete Workflow Example

From research to verified build:

```bash
# Phase 1: Research (manual web research)
# Theme: Moe's Tavern from The Simpsons
# - 5 rooms (Main Bar, Men's Room, Ladies Room, Back Room, Secret Room)
# - 23 objects (bar counter, stools, pool table, etc.)
# - 3 NPCs (Moe, Barney, Homer)
# - 13 interactive verbs (call, drink, play, talk, etc.)

# Phase 2: Generate YAML
# Create: extras/skills/game-designer/environments/moes-tavern.yaml
# (See example file for complete structure)

# Phase 3: Validate YAML
python extras/skills/game-designer/tools/build_from_yaml.py \
  --dry-run extras/skills/game-designer/environments/moes-tavern.yaml

# Output:
# Loaded environment: Moe's Tavern
#   Hash mode: enabled
#   Rooms: 5
#   Objects: 23
#   NPCs: 3
#   Verbs: 13

# Phase 4: User reviews YAML, approves build

# Phase 5: Execute build
python extras/skills/game-designer/tools/build_from_yaml.py \
  extras/skills/game-designer/environments/moes-tavern.yaml

# Output: ~1,200 lines over ~3-4 minutes
# Result: Test verb test-moes-tavern-abc123 passes all checks

# Phase 6: Verify in-game
# SSH to MOO, run: test-moes-tavern-abc123
# Explore the environment, test verbs
```

**Result**: Fully functional 5-room environment with interactive objects, NPCs, and verbs. Content is version-controlled in YAML and can be rebuilt at any time.

## Reference Files

- `references/moo-commands.md` — exact syntax for all build commands
- `references/verb-patterns.md` — RestrictedPython code patterns for interactive verbs
- `references/object-model.md` — parent classes, properties, exits, NPCs
- `references/room-description-principles.md` — guidelines for writing effective room descriptions
- `references/build-automation.md` — YAML schema and automated build patterns
- `assets/test-verb-template.md` — `@test-<name>` verb template (for custom tests)
- `environments/moes-tavern.yaml` — complete working example (5 rooms, 23 objects, 3 NPCs)
