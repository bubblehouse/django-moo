"""
Intermediate representation dataclasses for ZIL world elements.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ZilExit:
    direction: str  # "NORTH", "EAST", etc.
    dest: str | None  # room atom, or None for blocked/procedural
    message: str | None  # nogo message for string-only exits
    condition: str | None  # flag atom for conditional IF exits
    else_message: str | None  # fallback message when condition is false
    per_routine: str | None  # routine name for PER exits


@dataclass
class ZilRoom:
    atom: str  # ZIL identifier (e.g. "WEST-OF-HOUSE")
    desc: str  # short title shown in room header
    ldesc: str | None  # long description body
    fdesc: str | None  # first-visit description
    exits: list[ZilExit] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    globals: list[str] = field(default_factory=list)  # globally-visible scenery atoms
    action: str | None = None  # ACTION routine name
    value: int = 0  # discovery score points
    pseudo: list[tuple[str, str]] = field(default_factory=list)  # ("word", routine) pairs


@dataclass
class ZilObject:
    atom: str  # ZIL identifier
    location: str | None  # container atom (room or object)
    synonyms: list[str] = field(default_factory=list)
    adjectives: list[str] = field(default_factory=list)
    desc: str | None = None  # short name / brief description
    ldesc: str | None = None  # long description
    fdesc: str | None = None  # first-visit description
    text: str | None = None  # readable content (books, signs)
    flags: list[str] = field(default_factory=list)
    action: str | None = None
    capacity: int = 0
    size: int = 5
    value: int = 0
    tvalue: int = 0  # treasure value toward score


@dataclass
class ZilRoutine:
    name: str
    raw_body: str  # raw ZIL source text for stub comments


# Directions that are treated as exits in ROOM definitions
DIRECTION_ATOMS = frozenset(
    [
        "NORTH",
        "SOUTH",
        "EAST",
        "WEST",
        "NE",
        "NW",
        "SE",
        "SW",
        "UP",
        "DOWN",
        "IN",
        "OUT",
        "LAND",
    ]
)

# Direction → canonical alias for DjangoMOO exits
DIRECTION_ALIASES: dict[str, list[str]] = {
    "NORTH": ["north", "n"],
    "SOUTH": ["south", "s"],
    "EAST": ["east", "e"],
    "WEST": ["west", "w"],
    "NE": ["northeast", "ne"],
    "NW": ["northwest", "nw"],
    "SE": ["southeast", "se"],
    "SW": ["southwest", "sw"],
    "UP": ["up", "u"],
    "DOWN": ["down", "d"],
    "IN": ["in", "enter"],
    "OUT": ["out", "exit"],
    "LAND": ["land"],
}

# ZIL object flags and their DjangoMOO property mapping
FLAG_PROPERTIES: dict[str, tuple[str, object]] = {
    "TAKEBIT": ("takeable", True),
    "OPENBIT": ("open", True),
    "DOORBIT": ("is_door", True),
    "LIGHTBIT": ("lit", True),
    "BURNBIT": ("flammable", True),
    "READBIT": ("readable", True),
    "DRINKBIT": ("drinkable", True),
    "FOODBIT": ("edible", True),
    "NDESCBIT": ("obvious", False),
    "TRANSBIT": ("transparent", True),
    "WEAPONBIT": ("weapon", True),
    "FIGHTBIT": ("hostile", True),
    "VEHBIT": ("vehicle", True),
    "CLIMBBIT": ("climbable", True),
    "TURNBIT": ("turnable", True),
    "SEARCHBIT": ("searchable", True),
}

# Room-specific flags
ROOM_FLAG_PROPERTIES: dict[str, tuple[str, object]] = {
    "ONBIT": ("dark", False),  # room is lit
    "RLANDBIT": ("outdoor", True),
    "SACREDBIT": ("sacred", True),
    "MAZEBIT": ("maze", True),
}
