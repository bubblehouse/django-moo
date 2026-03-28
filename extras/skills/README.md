# Claude Code Skills

This directory contains custom Claude Code skills for the django-moo project. Each skill is a self-contained directory with a `SKILL.md` (the AI agent prompt) and a `references/` folder with supporting documentation.

## Skills

| Skill | What it does |
|-------|-------------|
| [verb-author](verb-author/README.md) | Write, review, and debug DjangoMOO verb files |
| [game-designer](game-designer/README.md) | Design and build themed multi-room MOO environments |
| [tech-librarian](tech-librarian/README.md) | Sync documentation across Sphinx, skill files, and AGENTS.md |
| [sandbox-auditor](sandbox-auditor/README.md) | Security audit passes on the RestrictedPython verb sandbox |

## How skills are loaded

Claude Code loads skills from `~/.claude/skills/`. The project-level skills here are symlinked into that directory so they are available in any conversation within this repository:

```
.claude/skills/verb-author       -> ../../extras/skills/verb-author
.claude/skills/game-designer     -> ../../extras/skills/game-designer
.claude/skills/tech-librarian    -> ../../extras/skills/tech-librarian
.claude/skills/sandbox-auditor   -> ../../extras/skills/sandbox-auditor
```

The symlinks live in `.claude/skills/` at the project root (not in `~/.claude/`). Claude Code discovers them as project-scoped skills.

To add a new skill, create a directory here with a `SKILL.md`, then symlink it:

```bash
ln -s ../../extras/skills/my-skill .claude/skills/my-skill
```

## Skill file structure

```
skill-name/
  SKILL.md          # AI agent instructions — the skill "prompt"
  README.md         # Human-readable docs (this kind of file)
  references/       # Supporting reference documents read by the agent
  assets/           # Templates, examples (optional)
  tools/            # Python scripts invoked by the skill (optional)
  environments/     # Build artifacts, e.g. YAML for game-designer (optional)
  snippets/         # Copy-paste patterns (optional)
```

`SKILL.md` must have a YAML frontmatter block with at minimum `name` and `description`:

```yaml
---
name: my-skill
description: One-line description used by Claude to decide when to invoke this skill.
---
```

The `description` field is what Claude Code matches against when deciding whether to auto-invoke a skill. Make it specific to the task domain.
