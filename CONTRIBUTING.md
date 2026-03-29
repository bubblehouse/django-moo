# Contributing to DjangoMOO

Thank you for your interest in contributing to DjangoMOO! This guide is meant to cover everything you need to get from zero to a merged contribution.

## Table of Contents

- [Contributing to DjangoMOO](#contributing-to-djangomoo)
  - [Table of Contents](#table-of-contents)
  - [Code of Conduct](#code-of-conduct)
  - [Ways to Contribute](#ways-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Development Setup](#development-setup)
    - [Prerequisites](#prerequisites)
    - [First-time setup](#first-time-setup)
    - [Start the services](#start-the-services)
    - [Bootstrap the database](#bootstrap-the-database)
    - [Verify the setup](#verify-the-setup)
  - [Project Structure](#project-structure)
  - [Code Style](#code-style)
    - [Formatter](#formatter)
    - [Linter](#linter)
    - [General conventions](#general-conventions)
  - [Testing](#testing)
    - [Running the test suite](#running-the-test-suite)
    - [What to test](#what-to-test)
    - [Writing tests](#writing-tests)
  - [Commit Messages](#commit-messages)
    - [Format](#format)
    - [Types](#types)
    - [Scopes](#scopes)
    - [Examples](#examples)
  - [Merge Request Process](#merge-request-process)
  - [Adding Dependencies](#adding-dependencies)
  - [Writing Verb Code](#writing-verb-code)
    - [File format](#file-format)
    - [Verb function context](#verb-function-context)
    - [Key patterns](#key-patterns)
    - [Testing verbs](#testing-verbs)
  - [Documentation](#documentation)
  - [Getting Help](#getting-help)

---

## Code of Conduct

This project follows a simple principle: be respectful, constructive, and collaborative. Harassment, discrimination, or bad-faith behaviour will not be tolerated. If you experience a problem, contact the maintainer at <phil@bubblehouse.org>.

---

## Ways to Contribute

- **Bug reports** — open an issue describing what went wrong
- **Feature requests** — open an issue describing what you'd like and why
- **Code** — fix a bug, implement a feature, improve performance
- **Tests** — increase coverage or add missing test cases
- **Documentation** — improve the user guide, API docs, or this file
- **Verb code** — contribute new or improved default game verbs

---

## Reporting Bugs

Before opening an issue, search existing issues to avoid duplicates.

When filing a bug, include:

1. DjangoMOO version (from `pyproject.toml` or `uv run python -c "import moo; print(moo.__version__)"`)
2. Python version (`python --version`)
3. Steps to reproduce the problem
4. What you expected to happen
5. What actually happened (paste the full traceback)
6. Relevant configuration (Docker Compose, settings overrides, etc.)

---

## Suggesting Features

Open an issue with the `enhancement` label. Describe:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you considered

It helps to discuss significant changes before writing code so you don't spend time on something that won't fit the project's direction.

---

## Development Setup

### Prerequisites

- Python 3.11 (the project pins `>=3.11,<3.12`)
- [uv](https://docs.astral.sh/uv/) — Python package and project manager
- Docker and Docker Compose
- `pre-commit`

### First-time setup

```bash
git clone https://gitlab.com/bubblehouse/django-moo
cd django-moo

# Install pre-commit hooks (runs linting and formatting on every commit)
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

### Start the services

```bash
docker compose up
```

This starts PostgreSQL, Redis, Celery workers, and the uWSGI application server.

### Bootstrap the database

```bash
docker compose run webapp manage.py migrate
docker compose run webapp manage.py collectstatic
docker compose run webapp manage.py moo_init
docker compose run webapp manage.py createsuperuser --username wizard
docker compose run webapp manage.py moo_enableuser --wizard wizard Wizard
```

### Verify the setup

| Service | URL |
|---------|-----|
| WebSSH client | <https://localhost/> |
| Django admin | <https://localhost/admin> |
| SSH direct | `ssh localhost -p 8022` |

---

## Project Structure

```
moo/
  core/           Core game engine: models, code execution, parser, permissions
  core/tests/     Unit and integration tests for the engine
  bootstrap/      Database initialisation and default game world
    default_verbs/        Verb source files installed on default objects
    default_verbs/tests/  Integration tests for those verbs
  shell/          AsyncSSH server and interactive prompt
  settings/       Django configuration (base, dev, test, local)
docs/             Sphinx source for the user guide and API reference
extras/           Helm chart, Nginx config, uWSGI config, WebSSH template
```

Key files:

| File | Purpose |
|------|---------|
| `moo/core/models/` | Django ORM models (Object, Verb, Property, Permission) |
| `moo/core/code.py` | RestrictedPython compilation and verb execution |
| `moo/core/parse.py` | Command parser and verb dispatch |
| `moo/bootstrap/default.py` | Default game world definition |
| `moo/conftest.py` | Shared pytest fixtures (`t_init`, `t_wizard`) |
| `pyproject.toml` | Dependency management and tool configuration |

---

## Code Style

### Formatter

The project uses [Ruff](https://docs.astral.sh/ruff/formatter/) with a line length of 120 characters.

```bash
uv run ruff format moo
```

### Linter

[Pylint](https://pylint.readthedocs.io/) is used for static analysis. The minimum acceptable score is **8.0 / 10**.

```bash
DJANGO_SETTINGS_MODULE=moo.settings.test uv run pylint moo
```

### General conventions

- Follow [PEP 8](https://peps.python.org/pep-0008/) except where Black overrides it.
- **Variables and functions:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `SCREAMING_SNAKE_CASE`
- **File names:** `snake_case`
- Write type hints in new code.
- Comments and docstrings are complete sentences ending with a period.
- Docstrings follow Google/NumPy style.
- Imports are ordered: stdlib, then third-party, then local — Black handles formatting automatically.
- Use the Django ORM exclusively; never build raw SQL with user-supplied input.

---

## Testing

### Running the test suite

```bash
# All tests, in parallel, with coverage
uv run pytest -n auto --cov

# A single file
uv run pytest moo/core/tests/test_parser.py

# View coverage after the run
uv run coverage report
```

### What to test

Every bug fix and new feature must include corresponding tests. Coverage must not decrease with your change.

There are two kinds of tests:

| Kind | Location | What it tests |
|------|----------|---------------|
| Core unit/integration | `moo/core/tests/` | Models and the execution engine against the `test` bootstrap dataset |
| Verb integration | `moo/bootstrap/default_verbs/tests/` | Verb behaviour against a fully initialised default world |

### Writing tests

**Fixtures:** Use `t_init` and `t_wizard` from `moo/conftest.py`. Bootstrap tests require:

```python
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_something(t_init, t_wizard):
    ...
```

**Capturing player output:** Pass a writer callback to `code.ContextManager`:

```python
printed = []
with code.ContextManager(t_wizard, printed.append):
    parse.interpret(ctx, "look")
assert "You see" in printed[0]
```

**Database state:** Always call `obj.refresh_from_db()` before asserting fields that may have changed during a verb call.

**Low-level output:** In the test environment, `write()` emits a `RuntimeWarning` instead of sending to a connection. Capture it with `pytest.warns(RuntimeWarning)`.

---

## Commit Messages

DjangoMOO uses the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification. This is enforced by `commitlint` via the pre-commit `commit-msg` hook, and drives automated semantic versioning on the `main` branch.

### Format

```
<type>(<scope>): <subject>

<body>
```

- **Subject:** lowercase, imperative mood, no trailing period, 50 characters max.
- **Body:** optional; explain *what* and *why*, not *how*; wrap at 72 characters.

### Types

| Type | When to use |
|------|-------------|
| `feat` | A new feature visible to users or game authors |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace — no logic change |
| `refactor` | Code change that is neither a fix nor a feature |
| `test` | Adding or fixing tests |
| `chore` | Build process, dependency updates, tooling |
| `ci` | CI/CD pipeline changes |

### Scopes

Use the module or component affected: `core`, `shell`, `bootstrap`, `admin`, `docs`, `helm`, `ci`.

### Examples

```
feat(core): add object property inheritance
fix(shell): handle SSH disconnect during verb execution
docs(readme): update quick-start instructions
test(core): add coverage for permission denial cases
chore(deps): upgrade celery to 5.5
```

Breaking changes must include a `BREAKING CHANGE:` footer:

```
feat(core)!: remove deprecated Object.get_property_value()

BREAKING CHANGE: Use Object.get_property() instead.
```

---

## Merge Request Process

1. **Branch** off `main`:

   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** following the style and testing guidelines above.

3. **Run checks locally** before pushing:

   ```bash
   uv run pytest -n auto --cov
   DJANGO_SETTINGS_MODULE=moo.settings.test uv run pylint moo
   ```

4. **Push** and open a Merge Request targeting `main` on GitLab.

5. **Describe your MR:**
   - What changed and why
   - Whether there are breaking changes
   - Link to any related issues

6. **CI must pass.** The pipeline runs lint and tests automatically on every MR that touches Python files. A Pylint score below 8.0 or any failing test blocks the merge.

7. **Address review feedback** with additional commits (no force-pushing during review).

8. After merge, semantic-release automatically determines the next version from the commit history and publishes a Docker image.

---

## Adding Dependencies

Runtime dependencies:

```bash
uv add <package>
```

Development-only dependencies:

```bash
uv add --group dev <package>
```

`uv.lock` is updated automatically. Include a brief note in your MR description explaining why the new dependency is needed. Avoid adding packages that duplicate functionality already provided by the stack.

To update all dependencies to the latest compatible versions:

```bash
uv lock --upgrade
```

Review changelogs carefully before committing major version bumps.

---

## Writing Verb Code

Verbs are Python functions that run inside a [RestrictedPython](https://restrictedpython.readthedocs.io/) sandbox. They live under `moo/bootstrap/default_verbs/`.

### File format

Every verb file starts with a shebang that registers it on an object:

```python
#!moo verb @dig --on $room --dspec any
obj = create(args[0], parents=[this])
obj.location = this
print(f"You create {obj.title()}.")
```

The `--on` parameter accepts `$<name>` to reference properties on the system object, otherwise it will look up the object by the provided name. Optional flags include `--dspec` (`any`, `this`, `either`) to control direct-object matching.

### Verb function context

Verb source files contain only the *body* of this implicit function:

```python
def verb(this, passthrough, _, *args, **kwargs):
    """
    this:        The object where the verb was found.
    passthrough: Call this to invoke the verb on parent objects.
    _:           The system object (#1).
    args/kwargs: Arguments when the verb is called as a method.
    """
```

Pylance will warn about `this`, `passthrough`, `_`, `args`, and `kwargs` being undefined — ignore those warnings, they are injected by the runtime.

### Key patterns

- Use `print()` for player-visible output. `return "..."` exits the verb but the string is not automatically displayed.
- Use `context.player` to identify the initiating player when a `--dspec` is set; `this` may be the matched object, not the caller.
- Use `obj.set_property("key", value)` to persist properties, not bare attribute assignment.
- Use `obj.parents.all()` to iterate a parent list (it is a `ManyToManyField`).

### Testing verbs

Write an integration test in `moo/bootstrap/default_verbs/tests/` using the `t_init` / `t_wizard` fixtures and `parse.interpret()` to drive the full command pipeline.

---

## Documentation

- **API docs** are generated by Sphinx from docstrings and published automatically to ReadTheDocs on every merge to `main`.
- **User guide** lives in `docs/source/guide/` as Markdown files.
- Update `docs/` for any user-facing change.
- Keep `README.md` current with quick-start instructions.
- If you add a significant new component or change the architecture, update `AGENTS.md` as well so AI-assisted development stays accurate.

---

## Getting Help

- **Issues:** <https://gitlab.com/bubblehouse/django-moo/-/issues>
- **Documentation:** <https://django-moo.readthedocs.io/>
- **Email:** <phil@bubblehouse.org>
