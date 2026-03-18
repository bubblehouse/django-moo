# `@test-<name>` Verb Template

Place this verb on `$programmer` so any programmer can run it:
```
@edit verb test-<name> on "$programmer"
```

Then paste the code below, replacing all `# TODO` placeholders.

---

## Full Template

```python
from moo.sdk import lookup, NoSuchObjectError, NoSuchVerbError

passed = 0
failed = 0

def ok(label):
    global passed
    passed += 1
    print(f"[green]PASS[/green] {label}")

def fail(label, reason=""):
    global failed
    failed += 1
    suffix = f": {reason}" if reason else ""
    print(f"[red]FAIL[/red] {label}{suffix}")

print("[bold]--- Room checks ---[/bold]")

# TODO: Add one block per expected room.
# Pattern: lookup by exact name, PASS if found, FAIL with reason if not.

try:
    main_room = lookup("TODO: Main Room Name")
    ok("Main Room exists")
except NoSuchObjectError as e:
    main_room = None
    fail("Main Room exists", str(e))

try:
    second_room = lookup("TODO: Second Room Name")
    ok("Second Room exists")
except NoSuchObjectError as e:
    second_room = None
    fail("Second Room exists", str(e))

# ... repeat for all rooms ...


print("[bold]--- Exit checks ---[/bold]")

# TODO: For each expected exit, check that the exit's dest matches the expected room.
# Pattern: iterate room.exits.all(), match by direction alias or name, check dest.

if main_room:
    found_north = False
    for exit_obj in main_room.exits.all():
        try:
            dest = exit_obj.get_property("dest")
            if second_room and dest.id == second_room.id:
                found_north = True
                break
        except Exception:
            pass
    if found_north:
        ok("Main Room -> north -> Second Room")
    else:
        fail("Main Room -> north -> Second Room", "exit or dest not found")

# ... repeat for all exit pairs ...


print("[bold]--- Object checks ---[/bold]")

# TODO: For each expected object in each room, check that it's present in contents.
# Pattern: iterate room.contents.all(), match by name substring or exact name.

if main_room:
    names_in_main = [o.name for o in main_room.contents.all()]
    target = "TODO: object name"
    if any(target.lower() in n.lower() for n in names_in_main):
        ok(f"'{target}' in Main Room")
    else:
        fail(f"'{target}' in Main Room", f"found: {names_in_main}")

# ... repeat for all expected objects ...


print("[bold]--- NPC checks ---[/bold]")

# TODO: For each NPC, check presence and that the speak verb exists.
# Pattern: lookup NPC by name, check location, check get_verb("speak").

try:
    npc = lookup("TODO: NPC Name")
    ok("NPC exists")
    try:
        npc.get_verb("speak")
        ok("NPC has speak verb")
    except NoSuchVerbError:
        fail("NPC has speak verb", "NoSuchVerbError")
    except Exception as e:
        fail("NPC has speak verb", str(e))
except NoSuchObjectError as e:
    fail("NPC exists", str(e))

# ... repeat for all NPCs ...


print("[bold]--- Verb checks ---[/bold]")

# TODO: For each parent class, check that key verbs exist.
# Pattern: lookup class by name, call get_verb, PASS/FAIL.

try:
    glass_class = lookup("TODO: Generic Class Name")
    try:
        glass_class.get_verb("TODO: verb name")
        ok("Generic Class has 'verb' verb")
    except NoSuchVerbError:
        fail("Generic Class has 'verb' verb", "NoSuchVerbError")
    except Exception as e:
        fail("Generic Class has 'verb' verb", str(e))
except NoSuchObjectError as e:
    fail("Generic Class exists", str(e))

# ... repeat for all parent classes and their key verbs ...


print(f"[bold]{passed}/{passed+failed} checks passed.[/bold]")
```

---

## Usage Notes

- All room lookups use `lookup()`, which raises `NoSuchObjectError` if not found.
- Store room objects in local variables so exit and contents checks can reference them.
- Use `room.exits.all()` to iterate exits; check `exit_obj.get_property("dest")` for connectivity.
- Use `room.contents.all()` for object presence; match names with `in` for substring matching.
- Use broad `except Exception` for verb/property checks — the specific exception type doesn't matter for the test output.
- Rich markup (`[green]`, `[red]`, `[bold]`) renders in the MOO terminal.
- Final summary line format: `N/N checks passed.`
- The total count includes both passed and failed: `passed + failed`.
