# Why the ZIL Importer Exists

The `zork1` dataset shipped with django-moo is the original Infocom
*Zork I: The Great Underground Empire*, translated into a DjangoMOO
bootstrap. This page explains how that translation works and the
trade-offs the importer makes. For function reference and the public
API surface, see {doc}`../reference/zil-importer`.

## The problem

In November 2025, Microsoft and Activision released the source code
for *Zork I*, *II*, and *III* under the MIT License. The source is
written in ZIL — Zork Implementation Language — an MDL/Lisp dialect
that compiles to Z-Machine bytecode. That bytecode runs on Z-Machine
interpreters like Frotz; it does *not* run on a multi-user persistent
world server.

Two paths are available for hosting the released source on DjangoMOO:

1. **Embed a Z-Machine.** Implement the Z-Machine in a verb and
   expose it as a player-controllable game session. Faithful, but
   conceptually a virtual machine running inside an unrelated runtime
   — none of the rooms, objects, or verbs participate in the MOO's
   object graph, the persistence layer, or the parser.
2. **Translate ZIL to MOO.** Compile the ZIL source into native MOO
   objects and verbs. The world becomes a first-class part of the
   MOO; rooms are real `Object` rows, exits are real `Exit` objects,
   and translated routines are real verbs that the parser can find.

The importer takes the second path. The bootstrap package it produces
uses the same `010_classes.py` / `020_rooms.py` / verb-file layout that
{doc}`../tutorials/custom-world` walks through.

## Bridging two semantic models

ZIL and Python have different semantic models, and the translator
spends most of its complexity bridging them. Concretely:

- **State versus objects.** ZIL globals serve dual purpose: some name
  in-game objects (`,LAMP` is the lamp object), some name flags
  (`,CYCLOPS-FLAG` is a state bit). The importer can't tell which is
  which from the form alone, so the converter enumerates rooms and
  objects up-front and passes that inventory to the translator. Atoms
  in the inventory translate to `lookup("name")`; everything else
  routes through `_.zork_sdk.zstate_get('NAME')`.
- **Implicit return.** ZIL routines return the value of their last
  expression. Python expression-statements are just discarded. The
  translator wraps the trailing expression of every routine in
  `return` so the implicit return becomes explicit.
- **Routine dispatch versus verb dispatch.** ZIL routines are first-
  class procedures called by name; MOO verbs are dispatched on a
  target object. The translator emits routine calls as
  `_.zork_thing.invoke_verb("name", *args)` so the dispatch ends up
  on the parent class that hosts the translated verb file.
- **The Z-Machine has no parser.** ZIL games dispatch through a
  hand-rolled grammar table; DjangoMOO has its own parser. The
  importer translates routines (the action handlers), not the
  command vocabulary. The `take` / `drop` / `examine` verbs that
  players actually type live under `verbs/commands/` — that
  subdirectory is part of the importer's output but isn't regenerated
  by routine translation, because commands need the LambdaMOO-style
  verb dispatch contract that doesn't fall out of ZIL routine bodies.

## Pipeline shape

The pipeline is four single-responsibility stages, each tested
independently:

```text
*.zil  ──► parser ──► converter ──► translator ──► generator ──► moo/bootstrap/<name>/
         (tokens   (IR dataclasses)  (per-routine    (per-bootstrap
          + AST)                      Python text)    file emission)
```

Splitting the work this way isolates the parts that have to change
when the upstream source moves:

- A new ZIL idiom — a form the translator doesn't yet recognise —
  changes only the translator. Parser and converter are unchanged.
- A new IR field (e.g., room scenery, NPC schedule) changes the
  converter and the IR dataclass. Parser unchanged.
- A new file in the generated bootstrap (e.g., a separate
  `015_tables.py` for ZIL `<TABLE>` data) changes only the
  generator. Translator unchanged.
- A new ZIL syntax (improbable — ZIL hasn't moved in 40+ years —
  but, e.g., extending to ZIL 6 dialects) changes only the parser.

This split also makes the importer reusable for non-Zork inputs.
Any text-adventure source that compiles to objects, rooms, exits,
and per-object handlers can be retargeted by writing a different
parser and converter; the translator and generator (with minor
adjustments to the recognised SDK call set) carry over.

## Why distinguish strings from atoms

A subtle parser detail worth calling out: ZIL has no type-level
distinction between `"hello"` (a string literal) and `HELLO` (an
atom). Both lex to the same Python `str`. The translator absolutely
needs to tell them apart — `<TELL "ALL CAPS">` emits a Python string
literal, but `<COND (,ALL-CAPS …)>` emits a state read.

The fix is a `Str` subclass of `str` that the parser tags string
literals with. `isinstance(node, str)` keeps working everywhere; only
the translator looks at `isinstance(node, Str)` to discriminate.
This is a small change that prevents a class of bug where all-caps
prose (which is common in interactive fiction) gets misinterpreted
as a globally-scoped lookup key.

## Why predicate atoms parse as one token

Another tokenizer detail: ZIL uses `?` as a predicate suffix — `LIT?`,
`STOLE-LIGHT?`, `0?`, `1?`. The bare-number forms (`0?`, `1?`) are
the ones that bite a naive tokenizer, because the regex for numbers
matches greedily before the regex for atoms gets a chance. The fix
is a negative lookahead on the number regex:

```python
r"(?P<number>-?\d+(?![A-Za-z0-9_.?!*#+\-]))"
```

so `0?` lexes as one atom (the head of `<0? .WD>`) rather than as
`0` followed by `?` followed by `.WD`. Without this, the form's head
is no longer a string and translation degenerates to a Python list
literal that pylint flags as a constant-test.

## Regeneration as a development workflow

For users of django-moo, the importer is invisible — `moo/bootstrap/zork1/`
is committed to the repo and loads the same way `default` does. The
importer only re-runs when the importer itself is being changed (a new
ZIL idiom, a translator bug fix, an upstream source bump). The
edit-compile cycle is:

1. Edit `extras/zil_import/{translator,parser,converter,generator}.py`.
2. Run `uv run python -m extras.zil_import …` to regenerate.
3. Run pylint over `moo/bootstrap/zork1/` and the importer.
4. Run `uv run pytest -n auto moo/bootstrap/zork1/` to verify the
   regenerated bootstrap still loads and behaves.

## See also

- {doc}`../reference/zil-importer` — the public API surface, IR
  dataclass fields, translation idioms, and CLI flags.
- {doc}`../reference/bootstrapping` — the contract the importer
  emits against (`initialize_dataset`, `get_or_create_object`,
  `load_verbs`).
- {doc}`../tutorials/custom-world` — the package layout the
  importer reproduces, with a step-by-step walkthrough.
- The upstream Zork I source, MIT-licensed:
  <https://github.com/the-infocom-files/zork1>
