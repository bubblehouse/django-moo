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

### Source

Toronto Film School — "Chekhov's Gun: Definition, Examples, and Tips"
https://www.torontofilmschool.ca/blog/chekhovs-gun-definition-examples-and-tips/
