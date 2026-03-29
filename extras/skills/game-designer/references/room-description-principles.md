# Room Description Principles

## Chekhov's Gun

Anton Chekhov's principle: every element introduced in a story should eventually matter. "One must never place a loaded rifle on the stage if it isn't going to go off."

Applied to room descriptions: **don't describe objects that players can't interact with, and don't make interactive objects invisible in the description.**

### What this means for MOO rooms

Every object mentioned in a room's `@describe` text should either:

1. **Be a real MOO object** the player can examine, take, manipulate, or trigger a verb on.
2. **Foreshadow a puzzle or event** — introduced early, paid off later in the same environment.

Conversely, every significant MOO object in a room should appear (or be strongly implied) in the room description. A button that players need to press but isn't mentioned in the description violates the inverse of the principle — the gun is loaded but hidden offstage.

### Practical rules for writing room `@describe` text

- **Name interactive objects explicitly.** If there's a `hounds button`, the description should say something like "a brass button engraved with two hounds." Players who read it will know to try `press button` or `examine button`.
- **Don't list furniture you haven't built.** If the description mentions a grandfather clock but there's no `grandfather clock` object, you've broken the contract. Either build the object or cut it from the description.
- **Use detail to signal importance.** A one-sentence mention = background flavor. A full sentence with specific sensory detail = "this matters." Use that contrast deliberately.
- **Exits can be Chekhov's Gun too.** A locked door described in room text should have a corresponding exit object and an unlock mechanic somewhere in the environment.
- **Foreshadow across rooms.** An NPC mentioned by name in one room ("Mr. Burns' voice echoes from down the hall") primes the player to find them. This is Chekhov's Gun across space rather than time.

### Anti-patterns to avoid

- Describing a "cluttered desk covered in papers" when there are no paper objects and no desk to examine — pure set dressing with no payoff.
- Building an object with a custom verb but not mentioning it anywhere in the room description — players will never discover it.
- Over-describing: listing ten objects when only two are interactive trains players to ignore descriptions entirely.

---

## The `obvious` Property

DjangoMOO objects have an `obvious` field (default `False`). Objects marked `obvious=True` appear automatically in the room contents listing when a player types `look`. Objects with `obvious=False` are invisible in the listing — discoverable only by interacting with them directly.

This property changes the Chekhov's Gun calculation:

- **`obvious: true` objects** are *listed* when a player looks at the room. They are the major, prominent room elements. They should also be mentioned in the room description — both the listing and the description point to them.
- **`obvious: false` objects** are hidden from the listing. They don't clutter the room display. They can still be mentioned or hinted at in the description as flavor or reward, but they don't *need* to be.

### Which objects deserve `obvious: true`?

Mark an object obvious when:

- It would be the first thing a person would notice walking into the room
- It has an interactive verb and players need to discover it
- It's a major architectural feature (fireplace, desk, bar counter)
- It's an NPC-scale presence (large taxidermy, a throne, a painting that dominates a wall)

Leave an object non-obvious when:

- It's a small detail discovered by examining a larger object (a poker by the fireplace, a ribbon in a crate)
- It's an Easter egg or reward for exploration (a hidden skeleton, a suspicious camera)
- Creating many copies via `quantity` — individual instances of fungible items usually don't need to appear in the listing

### Practical consequence for room descriptions

With `obvious` handling the listing problem, room descriptions no longer need to be exhaustive inventories. Write them as atmosphere and orientation, not a catalog. Mention the things that define the room's character. Trust the object listing to remind players what's interactable.

**Bad** (description as inventory):
> The room has a chandelier, two suits of armor, a portrait, a rug, and a doorbell mounted beside the entrance.

**Good** (description as atmosphere):
> The entrance hall stretches upward three stories, bathed in the cold glow of a crystal chandelier the size of a small automobile. Two suits of Gothic armor flank the entrance. An oil portrait of Mr. Burns dominates the north wall. Beside the entrance, a brass doorbell is mounted on a polished plate.

The second version names only the `obvious` objects, uses them to establish character, and lets the listing handle enumeration.

---

---

## Paragraph Breaks

Long single-block descriptions are hard to read. Break them into short paragraphs by topic using `\n\n` (a blank line between paragraphs). The build script converts YAML block scalars to escaped `\n\n` before sending to the server, and `at_describe.py` stores and renders them correctly.

**In YAML**, write paragraphs naturally in a block scalar — the build script handles escaping:

```yaml
rooms:
  - name: "The Library"
    description: |
      Floor-to-ceiling bookshelves line every wall, their upper reaches lost in shadow.
      The smell of old paper and wood polish is almost physical.

      A reading table dominates the center of the room, its leather surface worn smooth
      by decades of use. An oil lamp sits at one end, still faintly warm.

      A brass plaque above the door reads: "Knowledge is the only lamp that never dims."
```

**How to break by topic:**

- Paragraph 1 — overall atmosphere, first impression (what the room feels like)
- Paragraph 2 — the dominant object or focal point (the thing your eye goes to)
- Paragraph 3 — secondary details, exits, or interactive elements worth noting

Three paragraphs is usually enough. Two is fine. One long paragraph is almost always wrong.

**Object descriptions** follow the same rule. Anything longer than two sentences should be split:

```yaml
- name: "grandfather clock __hash_suffix__"
  description: |
    A mahogany grandfather clock stands nearly eight feet tall, its pendulum
    swinging with metronomic patience.

    The face is hand-painted with the phases of the moon. The time reads 11:57.
```

**Signs and notes** should also use paragraph breaks when the text warrants it. The `text` property of a `$note` supports `\n\n` the same way descriptions do.

### Source

Toronto Film School — "Chekhov's Gun: Definition, Examples, and Tips"
<https://www.torontofilmschool.ca/blog/chekhovs-gun-definition-examples-and-tips/>
