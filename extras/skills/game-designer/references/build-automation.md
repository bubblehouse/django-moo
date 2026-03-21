# Build Automation

For complex builds with many objects and verbs, manual command entry becomes impractical. This guide covers the YAML-driven build system.

## Overview

The game-designer skill uses a YAML-driven architecture that separates content (YAML files) from build logic (Python script).

**Architecture:**

1. **YAML environment files** (`environments/*.yaml`): Content definitions
   - Rooms, objects, NPCs, verbs
   - Human-readable, version-controlled
   - No Python knowledge required to edit

2. **build_from_yaml.py**: Generic build script
   - Reads any YAML environment file
   - Connects via SSH to MOO server
   - Executes wizard commands programmatically
   - Handles object ID tracking and verification

3. **moo_ssh.py**: SSH automation library
   - Connects via pexpect to MOO SSH server with `TERM=moo-automation` (disables CPR)
   - Uses PREFIX/SUFFIX delimiters for fast output detection (~0.1s per command)
   - Quiet mode (`QUIET enable`) disables Rich ANSI color codes for clean output
   - Strips ANSI escape sequences from captured output
   - Provides `run()`, `enable_delimiters()`, `enable_automation_mode()`

**Key benefits:**
- **Repeatable builds**: YAML defines exact environment
- **Version control**: Content changes are clear in diffs
- **Accessibility**: Non-programmers can edit YAML
- **Testing**: Optional hash suffixes for repeated builds
- **Automated verification**: Test verbs auto-generated

## YAML-Driven Build Workflow

### Step 1: Create YAML Environment File

Example: `environments/moes-tavern.yaml`

```yaml
metadata:
  name: "Moe's Tavern"
  description: "Classic dive bar from The Simpsons"
  author: "game-designer"
  version: "1.0"
  base_parent: "$thing"
  npc_parent: "$player"
  use_hash_suffix: true  # Optional hash for testing

rooms:
  - name: "Main Bar"
    description: "Dark, smoky dive bar..."
    exits:
      - direction: north
        to: "Back Room"

objects:
  "Main Bar":
    - name: "bar stool"
      description: "Wobbly bar stool..."
      aliases: ["stool"]
      obvious: true   # Appears in room listing when players look
      quantity: 4  # Create 4 identical stools

npcs:
  - name: "Moe Szyslak"
    description: "Surly bartender..."
    aliases: ["Moe"]
    room: "Main Bar"

verbs:
  - verb: "drink"
    object: "Duff beer"
    room: "Main Bar"
    code: |
      from moo.sdk import context
      print("You drink the beer...")
      this.delete()
```

### Step 2: Prepare the Server

For **local development**, a DB refresh and server restart before each build ensures a clean state and avoids accumulating stale objects across test runs. For **production deploys**, just run the build against the live server — no restart needed.

If the server goes down mid-build, restart webapp and celery:

```bash
docker compose restart webapp celery
```

Do **not** use `@reload` — it creates duplicate verbs on a freshly-bootstrapped DB.

### Step 3: Run Build Script

```bash
# Basic build (respects use_hash_suffix from YAML)
python extras/skills/game-designer/tools/build_from_yaml.py \
    extras/skills/game-designer/environments/moes-tavern.yaml

# Dry run (validate YAML without connecting)
python build_from_yaml.py --dry-run environments/moes-tavern.yaml

# Force hash mode (override YAML setting)
python build_from_yaml.py --hash environments/moes-tavern.yaml

# Production mode (clean names, no hash)
python build_from_yaml.py --no-hash environments/moes-tavern.yaml

# Skip test verb
python build_from_yaml.py --no-test environments/moes-tavern.yaml
```

### Step 3: Verify Build

The script automatically:
1. Creates all rooms and exits
2. Creates and places all objects
3. Creates and places all NPCs
4. Attaches all verbs
5. Generates test verb
6. Runs test verb

Build time: ~3-4 minutes for typical environments (5 rooms, 30+ objects)

## YAML Schema Reference

### metadata Section

```yaml
metadata:
  name: "Environment Name"          # Required
  description: "Brief description"  # Optional
  author: "game-designer"           # Optional
  version: "1.0"                    # Optional
  base_parent: "$thing"             # Default parent for objects
  npc_parent: "$player"             # Default parent for NPCs
  use_hash_suffix: true             # Enable hash mode (default: true)
```

**Hash Mode:**
- `true`: Adds `[abc123]` to all names (testing mode, repeatable builds)
- `false`: Clean names (production mode)
- CLI overrides: `--hash` or `--no-hash`

### rooms Section

```yaml
rooms:
  - name: "Room Name"
    description: "Detailed room description..."
    exits:
      - direction: north
        to: "Another Room"
      - direction: south
        to: "External Room"
        reverse: north  # Tunnel back to existing room
```

**Exit Types:**
- Without `reverse`: Create new room with `@dig`
- With `reverse`: Tunnel to existing room

### objects Section

```yaml
objects:
  "Room Name":
    - name: "object name"
      description: "Object description..."
      aliases: ["alias1", "alias2"]
      parent: "$thing"      # Optional, uses metadata.base_parent if omitted
      obvious: true         # Optional, makes object appear in room listing (default: false)
      quantity: 4           # Optional, creates N identical objects

    - name: "another object"
      # ... more object specs
```

**Key Features:**
- Organized by room for clarity
- `obvious: true` makes an object appear in the room contents listing when players `look`
- `quantity` field creates multiple identical objects
- Aliases added using `@alias` verb

**`obvious` guidelines:**
- Mark obvious the things a player would immediately notice: dominant furniture, interactive focal points, major props
- Leave non-obvious: small details, discoverable easter eggs, functional items that players find by examining other objects
- See `references/room-description-principles.md` for the full Chekhov's Gun / `obvious` relationship

### npcs Section

```yaml
npcs:
  - name: "NPC Name"
    description: "NPC description..."
    aliases: ["alias"]
    parent: "$player"     # Optional, uses metadata.npc_parent if omitted
    room: "Starting Room" # Optional, can be omitted for NPCs in void
```

### verbs Section

```yaml
verbs:
  - verb: "verb_name"
    object: "object name"  # Name of object to attach verb to
    room: "Room Name"      # Optional, for disambiguation
    code: |
      from moo.sdk import context
      # Verb implementation here
      # Multi-line code supported
```

**Verb Code:**
- Uses YAML literal block scalar (`|`)
- Full RestrictedPython syntax
- Access to `moo.sdk` imports
- `this` refers to the object

### test Section (Optional)

```yaml
test:
  rooms: ["Room 1", "Room 2"]
  objects:
    "Room 1": ["object1", "object2"]
  npcs: ["NPC1", "NPC2"]
  verbs:
    - {object: "object1", verb: "verb1"}
```

If omitted, test expectations are auto-generated from the YAML structure.

## Validation & Performance

### Build Testing Results

The YAML-driven build system has been validated against the original monolithic script:

**Test Configuration:**
- Environment: Moe's Tavern (5 rooms, 23 objects, 3 NPCs, 13 verbs)
- Server: Local DjangoMOO instance
- Method: Side-by-side comparison of both build approaches

**Results:**

| Metric | YAML-Based | Original Script | Improvement |
|--------|-----------|-----------------|-------------|
| Build Status | ✅ Success | ✅ Success | Equivalent |
| Output Lines | 1,191 | 1,355 | 13% reduction |
| Alias Commands | 48 (`@alias`) | 132 (`@eval`) | 64% reduction |
| Build Time | ~3-4 min | ~15-20 min | 4-5x faster |
| Rooms Created | 5 | 5 | ✅ |
| Objects Created | 23 | 23 | ✅ |
| NPCs Created | 3 | 3 | ✅ |
| Verbs Attached | 13 | 13 | ✅ |
| Test Verb | ✅ Pass | ✅ Pass | ✅ |

**Key Findings:**
- YAML approach produces equivalent results with cleaner output
- Using `@alias` verb reduces alias commands by 64%
- Overall output reduction of 13% improves readability
- Automation mode (delimiters + quiet) reduces build time from ~15-20 min to ~3-4 min
- Hash mode works correctly for repeated builds

### Efficiency Improvements

**Alias Handling:**
```bash
# Original approach (132 commands total for 23 objects with aliases)
@eval "from moo.sdk import lookup; lookup(45).add_alias('stool')"
@eval "from moo.sdk import lookup; lookup(45).add_alias('seat')"
# ... 130 more lines

# YAML approach (48 commands total)
@alias #45 as "stool"
@alias #45 as "seat"
# ... 46 more lines
```

**Output Comparison:**
- Original: Verbose `@eval` with full module paths
- YAML: Clean `@alias` commands
- Result: Easier to read, debug, and verify

## Legacy Script Reference

### build_moes_tavern.py (Reference Only)

Original monolithic script: `extras/skills/game-designer/tools/build_moes_tavern.py`

This script is preserved as a reference but should not be used for new builds. It demonstrates the patterns that `build_from_yaml.py` implements generically.

**Status**: Tested and validated. Produces equivalent results to YAML-based approach with slightly more verbose output.

### Hash-Based Naming

Each build run generates a 6-character hash (e.g., `e9dd2e`). All created objects include this hash:
- `Moe's Tavern [e9dd2e] - Main Bar`
- `bar stool [e9dd2e]`
- `Duff beer [e9dd2e]`

This allows:
- Multiple test builds without cleanup
- Parallel builds in same database
- Easy identification of build artifacts
- No conflicts with existing objects

### Object Creation Pattern

```python
def create(moo, name, parent="$thing"):
    """Create an object via @eval and return its #N reference."""
    escaped_name = name.replace('"', '\\"')
    escaped_parent = parent.replace('"', '\\"')

    output = moo.run(
        f'@eval "from moo.sdk import create, lookup; '
        f'obj = create(\\"{escaped_name}\\", '
        f'parents=[lookup(\\"{escaped_parent}\\")], '
        f'location=None); '
        f'print(f\\"Created {{obj}}\\"); '
        f'obj"'
    )

    # Extract #N from output like "Created #45 (bar stool [e9dd2e])"
    match = re.search(r"(#\d+)", output)
    return match.group(1) if match else None
```

Why `@eval` instead of `@create`:
- Bypasses parser ambiguity when 3+ objects share a name
- Parser resolves names *before* verb execution
- SDK `create()` function bypasses parser entirely

Why `location=None`:
- Avoids race conditions with `enterfunc`
- Allows batch object creation before placement
- Objects moved to rooms after creation/description/aliasing

### Moving Objects to Rooms

```python
def move_to_room(moo, obj_ref, room_name):
    """Move an object from void to room using @eval with moveto()."""
    obj_id = obj_ref.replace('#', '')
    escaped_room = room_name.replace('"', '\\"')

    moo.run(
        f'@eval "from moo.sdk import lookup; '
        f'lookup({obj_id}).moveto(lookup(\\"{escaped_room}\\"))"'
    )
```

The `@move` command won't work on objects in the void because it uses `context.parser` which only searches the local area.

### Adding Aliases

```python
def add_aliases(moo, obj_ref, aliases):
    """Add aliases using @alias command."""
    for alias in aliases:
        escaped_alias = alias.replace('"', '\\"')
        moo.run(f'@alias {obj_ref} as "{escaped_alias}"')
```

The `@alias` verb supports both object names and `#N` references with global lookup. This is simpler and faster than the previous `@eval` approach.

For programmatic access in special cases, `@eval` still works:

```python
def add_aliases_via_eval(moo, obj_ref, aliases):
    """Add aliases using @eval (alternative method)."""
    obj_id = obj_ref.replace('#', '')
    for alias in aliases:
        escaped_alias = alias.replace("'", "\\'")
        moo.run(
            f"@eval \"from moo.sdk import lookup; "
            f"lookup({obj_id}).add_alias('{escaped_alias}')\""
        )
```

### Describing Objects

**Critical**: descriptions must have `\`, `\n`, and `"` all escaped before being sent over SSH. YAML block scalars (`|`) produce strings with literal newlines — if those aren't escaped, pexpect splits the command at each newline, sending a malformed first line and a bare `"` as the second line.

```python
def describe(moo, ref, desc):
    """Describe an object by #N reference."""
    # Escape backslashes first, then newlines, then double-quotes
    escaped_desc = desc.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
    moo.run(f'@describe {ref} as "{escaped_desc}"')
```

The `at_describe.py` verb unescapes `\\n` back to real newlines before storing, so multiline descriptions are preserved correctly in the DB.

**Symptom if `\n` is missing**: the build log shows a `WARNING: could not get ID` for the object described immediately before a `@create`, and Wizard receives a lone `"` character in its output stream. The off-by-one was caused by this exact pattern across every description in the build.

### Verb Creation with Multi-line Code

```python
def set_verb(moo, verb_name, obj_ref, code):
    """Create verb via @edit ... with, escaping newlines."""
    # Escape backslashes, newlines, then quotes
    escaped = (code.replace("\\", "\\\\")
                   .replace("\n", "\\n")
                   .replace('"', '\\"'))

    if str(obj_ref).startswith("#"):
        moo.run(f'@edit verb {verb_name} on {obj_ref} with "{escaped}"')
    else:
        moo.run(f'@edit verb {verb_name} on "{obj_ref}" with "{escaped}"')
```

The `at_edit.py` verb unescapes `\\n` back to real newlines before storing.

### RestrictedPython Constraints in Generated Code

The test verb and any generated verb code runs inside the RestrictedPython sandbox. **Subscript augmented assignment is blocked at compile time:**

```python
# FAILS — RestrictedPython silently sets code.code = None, causing:
# TypeError: exec() arg 1 must be a string, bytes or code object
results["passed"] += 1

# CORRECT — use plain variables
passed += 1
failed += 1
```

The symptom of a compilation failure is `TypeError: exec() arg 1 must be a string, bytes or code object` when the verb is invoked. If this appears, inspect the generated code for any `dict["key"] += value` patterns.

### Build Phase Structure

```python
def main():
    run_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]

    with MooSSH() as moo:
        # Phase 1: Rooms and exits (static commands)
        for cmd in ROOMS:
            cmd_with_hash = cmd.replace("Moe's Tavern", f"Moe's Tavern [{run_hash}]")
            moo.run(cmd_with_hash)

        # Phase 2-6: Objects (dynamic, capture IDs, move to rooms)
        duff_ref = build_main_bar_objects(moo, run_hash)
        build_mens_room_objects(moo, run_hash)
        # ... etc

        # Phase 7: NPCs
        build_npcs(moo, run_hash)

        # Phase 8: Verbs
        for spec in VERBS:
            obj_name = f"{spec['obj']} [{run_hash}]"
            obj_ref = obj_refs.get(obj_name, obj_name)
            set_verb(moo, spec['verb'], obj_ref, spec['code'])

        # Phase 9: Test verb
        test_code = generate_test_verb_code(run_hash)
        set_verb(moo, f"test-moes-tavern-{run_hash}", "$programmer", test_code)

        # Run test
        moo.run(f"test-moes-tavern-{run_hash}")
```

### Output Capture

The MOO uses Celery tasks to process commands asynchronously. `moo_ssh.py` supports two output capture modes:

**Delimiter mode** (default when `enable_automation_mode()` is called): The server emits a PREFIX marker before command output and a SUFFIX marker after. The client polls for the suffix marker and returns as soon as it's seen — typically within 100ms of the Celery task completing. A 1-second settle delay is then applied before the next command.

**Timeout fallback** (used for PREFIX/SUFFIX setup commands themselves): Polls the PTY buffer over ~7.5s. Used automatically when delimiters aren't yet configured.

```python
# Delimiter mode — fast
with MooSSH() as moo:
    moo.enable_automation_mode()
    output = moo.run("look")  # returns in ~1.1s

# Timeout fallback (still works, just slow)
with MooSSH() as moo:
    output = moo.run("look")  # returns in ~7.5s
```

`expect(pexpect.TIMEOUT, timeout=N)` waits exactly N seconds (wall time), not "until output arrives". The delimiter approach avoids this entirely.

## Build Script Best Practices

1. **Generate unique identifiers per run** - allows repeated builds
2. **Create objects in the void** - avoid race conditions and location issues
3. **Capture all object IDs** - use `#N` refs for subsequent commands
4. **Move objects after creation** - batch placement after all attributes set
5. **Use @eval for duplicates** - bypass parser ambiguity when creating 3+ objects with same name
6. **Add aliases with @alias** - use `@alias #N as "alias"` instead of `@eval`
7. **Test after build** - automated verification catches issues early
8. **Log all commands** - verbose output helps debugging

## Timing Considerations

With automation mode enabled (the default), each command takes ~1.1s (0.1s execution + 1s settle delay). A 150-command build takes ~3-4 minutes.

Without automation mode (e.g., when connecting manually), each command takes ~7.5s due to CPR timeout delays — that's 15-20 minutes for the same build.

For faster iteration during development:
- Test individual commands interactively first
- Use smaller test builds (1-2 rooms)
- Create parent classes once, reuse across builds

## SSH Connection Details

```python
MooSSH(
    host="localhost",
    port=8022,
    user="phil",
    password="qw12er34",
    timeout=6  # Applies to delimiter wait loop; setup commands use timeout-based fallback
)
```

`MooSSH` connects with `TERM=moo-automation`, which the server detects to disable CPR (Cursor Position Request). CPR previously caused ~2-3s timeout delays per command. With CPR disabled and delimiters active, commands complete as soon as output is received.

Call `enable_automation_mode()` once after connecting to enable all optimizations:

```python
with MooSSH() as moo:
    moo.enable_automation_mode()  # enables delimiters + quiet mode
    moo.run("look")               # ~1.1s instead of ~7.5s
```

`build_from_yaml.py` calls `enable_automation_mode()` automatically.

## Troubleshooting

### Common Issues and Solutions

**Issue: "No such object" errors during build**
- **Cause**: Room name typo or case mismatch
- **Solution**: Verify room names in YAML match exactly (case-sensitive)
- **Prevention**: Use `--dry-run` to validate YAML before building

**Issue: "Ambiguous object" errors**
- **Cause**: Multiple objects with same name, no room context
- **Solution**: Add `room` field to verb definitions for disambiguation
- **Example**: `verb: "drink", object: "Duff beer", room: "Main Bar"`

**Issue: `WARNING: could not get ID` for an object**
- **Cause**: Description with unescaped newlines split the `@describe` command across lines, causing the output to appear in the wrong command's window. This was the root cause of the "off-by-one" bug.
- **Solution**: The `describe()` function in `build_from_yaml.py` now correctly escapes `\\`, `\n`, and `"`. If this reappears, check that all three are being escaped in the right order.

**Issue: Stray `"` appearing in Wizard output**
- **Cause**: An unescaped `\n` in a description caused pexpect to send the command as two lines. The second line was just the closing `"`.
- **Solution**: Covered by the `describe()` fix above.

**Issue: `TypeError: exec() arg 1 must be a string, bytes or code object` in test verb**
- **Cause**: RestrictedPython silently failed to compile the verb. Most likely a `dict["key"] += value` pattern.
- **Solution**: Use plain variables (`passed += 1`) instead of subscript augmented assignment.

**Issue: Duplicate verbs after `@reload`**
- **Cause**: `@reload` creates a new verb entry on a freshly-bootstrapped DB even when one already exists.
- **Solution**: Do not use `@reload`. User manages verb state by refreshing the DB before each build.

**Issue: SSH disconnects during build**
- **Cause**: Network timeout or MOO server restart
- **Solution**: Run `docker compose restart webapp celery` to restore the server, then re-run the build script

**Issue: Objects not appearing in rooms**
- **Cause**: `moveto()` failed or room name mismatch
- **Solution**: Check stderr output for move failures
- **Debugging**: SSH in, use `@show #N` to check object location

**Issue: Test verb failures with hash mode**
- **Cause**: Test expectations missing hash suffix
- **Solution**: Auto-generated tests include hash automatically
- **Manual fix**: Update test expectations to include `[hash]` in names

**Issue: Verbs not executing**
- **Cause**: Syntax error in verb code or wrong object reference
- **Solution**: Check verb code for Python errors, verify object exists
- **Debugging**: SSH in, use `@show "object"` to list verbs

**Issue: Build seems stuck**
- **Cause**: A command is waiting for its delimiter or timeout
- **Solution**: Each command takes ~1.1s in automation mode; 150 commands = ~3 minutes
- **If truly stuck**: The delimiter loop has a 6s timeout before giving up — check for SSH errors in output

### Build Performance Tips

1. **Run dry-run first**: Catches YAML errors before committing to a build
2. **Use hash mode for testing**: Allows repeated builds without cleanup
3. **Monitor stderr**: Progress messages show which phase is running
4. **Don't run multiple builds**: Wizard moves between rooms, causes conflicts
5. **Automation mode is automatic**: `build_from_yaml.py` calls `enable_automation_mode()` — no manual setup needed
