# Audience Translation Rules

## Diátaxis: Where Does the Content Belong?

Before porting anything to Sphinx, decide which Diátaxis category the content fits. Content in the wrong category is the most common structural problem — gotchas end up as reference entries, conceptual explanations get buried in how-to guides.

| Category | Purpose | Hallmark | Sphinx guide files |
|----------|---------|---------|-------------------|
| **Tutorial** | Learning by doing | Linear narrative, guided outcome | `01_introduction.md` |
| **How-to** | Solving a specific task | Goal-first, steps, no theory | `11_creating_verbs.md`, `12_more_verbs.md` |
| **Explanation** | Understanding a concept | "Why", trade-offs, context | `02_architecture.md`, `10_parser.md` |
| **Reference** | Lookup while working | Exhaustive, accurate, no narrative | `08_verbs.md`, `14_builtins.md`, `09_sandbox_security.md` |

**Quick classification for common skill content types:**

| Content type | Diátaxis category | Likely destination |
|---|---|---|
| API name correction (`get_pobj_str` not `get_pobj_string`) | Reference | `08_verbs.md` or `12_more_verbs.md` |
| Gotcha with explanation (`return "..."` not printing) | How-to or Reference | `11_creating_verbs.md` |
| New SDK function | Reference | `12_more_verbs.md` |
| Parser behavior (verb search order) | Explanation + Reference | `10_parser.md` |
| Sandbox restriction (new blocked import) | Reference | `09_sandbox_security.md` |
| New object class (`$furniture`) | Reference | `04_objects.md` |
| New workflow (YAML build process) | How-to | `15_development.md` or `16_bootstrapping.md` |

---

When porting content between layers, the facts stay the same but the framing changes significantly. The same truth reads differently for an AI agent following a task checklist versus a human developer reading documentation for the first time.

---

## Agent-Facing → Human-Facing (Skills/AGENTS.md → Sphinx)

Use this direction when porting a gotcha, correction, or API clarification from a skill or AGENTS.md into Sphinx.

**Replace WRONG/CORRECT tables with prose explanations.**

Agent facing:

```
WRONG: return "Player not found."
CORRECT: print("Player not found."); return
```

Human facing:
> Returning a string from a verb does not display it to the player. The return value is discarded by the dispatcher. Use `print()` to send output, then a bare `return` to exit early.

**Replace terse bullet rules with paragraphs that include context.**

Agent facing:

```
- obj.parents.all() required — ManyToManyField, not directly iterable
```

Human facing:
> The `parents` attribute is a Django `ManyToManyField`. Iterating it directly will raise a `TypeError`. Always call `.all()` first: `for parent in obj.parents.all()`.

**Add "why it matters."** Sphinx readers want to understand the behavior, not just avoid the trap. Explain what would go wrong without the rule.

**Remove workflow instructions.** Phase numbers, "run this next", "update memory" — none of that belongs in Sphinx. Strip it. The reader is not following a procedure.

**Add realistic verb scenarios.** An abstract rule about `get_dobj_str()` lands better when anchored to a concrete verb: a `@drop` command, a `@lock` command, something the reader can picture.

**Keep code examples but make them self-contained.** A snippet copied from a skill reference file may assume context. Expand it to a runnable minimum example.

---

## Human-Facing → Agent-Facing (Sphinx → Skills/AGENTS.md)

Less common. Use this direction when Sphinx gets a major structural update that introduces facts an AI agent needs at decision time.

**Distill prose into decision rules.** A three-paragraph Sphinx explanation becomes one bullet: the rule, when it applies, and what breaks if ignored.

**Use the `Why:` / `How to apply:` pattern for AGENTS.md corrections.**

```
Use `obj.parents.all()` to iterate parents.
Why: `parents` is a ManyToManyField — direct iteration raises TypeError.
How to apply: Any verb that loops over an object's inheritance chain.
```

**Minimize examples.** Skills assume the agent can read code. The shortest correct example that demonstrates the rule is enough.

**Remove "why it matters for beginners."** The agent knows why. Skip the orientation.

---

## Memory → Documentation Layers

Memory files (`~/.claude/projects/.../memory/`) capture ephemeral investigation results. They are not documentation. If a memory file contains a stable fact, port it.

**Port when:** The fact has been stable across multiple sessions (not a temporary workaround). The fact corrects a named API, describes a behavioral rule, or identifies a gotcha that will recur.

**Port to:** At minimum the layer most likely to surface it (skill reference file for an API correction, Sphinx for a behavioral rule). Ideally both.

**After porting:** The memory file can remain as a pointer, but should not be the only place the fact lives.

---

## Common Patterns Lost in Translation

These facts have a history of being correct in one layer but missing or wrong in another. Check these whenever doing a sync pass.

| Fact | Common gap |
|------|------------|
| `print()` output is buffered until Celery completes, arrives after PREFIX/SUFFIX | Missing from Sphinx entirely; in AGENTS.md and memory |
| `return "..."` does not display to player | In verb-author skill; often missing from Sphinx `11_creating_verbs.md` |
| `obj.parents.all()` required for iteration | In AGENTS.md; sometimes omitted from Sphinx object model section |
| `get_pobj_str` not `get_pobj_string` | In AGENTS.md corrections; may be stale in verb-author `parser-api.md` |
| `has_pobj_str` not `has_pobj_string` | Same |
| `--dspec either` for optional dobj | In verb-author skill; sometimes missing from `08_verbs.md` |
| `context.player` vs `this` when dspec is set | In AGENTS.md; needs a clear explanation in Sphinx parser section |
| `lookup()` raises `NoSuchObjectError`, never returns `None` | In AGENTS.md; often absent from Sphinx |
| f-string / `str.format` sandbox distinction | In memory; may need a Sphinx callout in `09_sandbox_security.md` |
| `line_editor=False` required for asyncssh + prompt_toolkit | In memory `editor-cursor-bug.md`; belongs in `17_connection_control.md` |
