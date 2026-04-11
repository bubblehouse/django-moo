#!moo verb look_self --on $room

# pylint: disable=return-outside-function,undefined-variable

"""
Override the $root_class definition of the verb `look_self` in order to provide a fuller description of a
room than the `description`` property gives. This verb prints a 3x3 compass grid showing available exits,
to the left of the room name and description, then the list of contents of the room.

The compass grid is suppressed entirely when the session is in quiet mode.
"""

from moo.sdk import get_session_setting, get_wrap_column

# Direction -> (row, col) in 3x3 grid (0-indexed)
GRID_POS = {
    "northwest": (0, 0), "north": (0, 1), "northeast": (0, 2),
    "west":      (1, 0),                  "east":      (1, 2),
    "southwest": (2, 0), "south": (2, 1), "southeast": (2, 2),
}

ARROWS = {
    "northwest": "\u2196", "north": "\u2191", "northeast": "\u2197",
    "west":      "\u2190",                    "east":      "\u2192",
    "southwest": "\u2199", "south": "\u2193", "southeast": "\u2198",
}

# Reverse map: (row, col) -> direction name
GRID_DIR = {v: k for k, v in GRID_POS.items()}

quiet = get_session_setting("quiet_mode", False)

if not quiet:
    existing = set()
    for d in GRID_POS:
        if this.match_exit(d):
            existing.add(d)

    has_up = bool(this.match_exit("up"))
    has_down = bool(this.match_exit("down"))
    if has_up and has_down:
        center = "[white]\u2195[/white]"
    elif has_up:
        center = "[white]\u25b2[/white]"
    elif has_down:
        center = "[white]\u25bc[/white]"
    else:
        center = " "

    compass_lines = []
    for row in range(3):
        cells = []
        for col in range(3):
            if row == 1 and col == 1:
                cells.append(center)
            else:
                d = GRID_DIR[(row, col)]
                arrow = ARROWS[d]
                if d in existing:
                    cells.append(f"[white]{arrow}[/white]")
                else:
                    cells.append(f"[color(238)]{arrow}[/color(238)]")
        compass_lines.append(" ".join(cells))

    # Compass is 5 visible chars wide ("↖ ↑ ↗"), plus 2-space separator = 7 prefix chars.
    SEP = "  "
    COMPASS_VISIBLE = 5
    TEXT_WIDTH = get_wrap_column() - 1 - COMPASS_VISIBLE - len(SEP)

    # Build the text block: title on line 1, wrapped description after.
    title_line = f"[color(226)]{this.title()}[/color(226)]"
    if this.get_property("dark"):
        text_lines = [title_line, "It's too dark to see anything."]
    else:
        description = this.get_property("description")
        if description:
            desc_wrapped = [f"[deep_sky_blue1]{line}[/deep_sky_blue1]" for line in _.string_utils.rewrap(description, TEXT_WIDTH).split("\n")]
            text_lines = [title_line] + desc_wrapped
        else:
            text_lines = [title_line]

    # Merge compass (3 lines) with text block side by side.
    # compass_lines always has exactly 3 entries.
    INDENT = " " * (COMPASS_VISIBLE + len(SEP))
    for i, left in enumerate(compass_lines):
        right = text_lines[i] if i < len(text_lines) else ""
        if right:
            print(f"{left}{SEP}{right}")
        else:
            print(left)
    for i in range(len(compass_lines), len(text_lines)):
        print(f"{INDENT}{text_lines[i]}")
else:
    print(f"[bright_yellow]{this.title()}[/bright_yellow]")
    if this.get_property("dark"):
        print("It's too dark to see anything.")
        return
    description = this.get_property("description")
    if description:
        print(description)

print("")
this.tell_contents()
