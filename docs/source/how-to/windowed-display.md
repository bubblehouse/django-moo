# Windowed Display

A verb can switch a player's rich (prompt_toolkit) session into a persistent
split-screen layout: a fixed top region you paint by coordinates (a status bar,
a small map, an ASCII HUD), a scrolling region that shows normal game output,
and an input line that works exactly as usual. This is a general display
capability — anything that wants a fixed on-screen panel can use it.

The functions live in `moo.sdk` and are **wizard-only** (the window owns the
player's screen, so only privileged verbs may drive it).

## Quick start

```python
from moo.sdk import context, open_window, window_write, close_window, window_supported

if not window_supported(context.player):
    print("Windowed display requires a rich (prompt_toolkit) client.")
    return

# Open a 5-row top region.
open_window(context.player, height=5, title="Status")

# Paint the top region by (row, col). Text may contain Rich markup.
window_write(context.player, 0, 0, "[bold]HP[/bold] 20/20   Score 0   Moves 0")
window_write(context.player, 2, 2, "+------+")
window_write(context.player, 3, 2, "|  [green]@[/green]   |")
window_write(context.player, 4, 2, "+------+")
```

While the window is open, the player types commands in the input line and the
results — plus any asynchronous `tell` output — appear in the scrolling region.
Call `close_window(context.player)` (or let the player press `Ctrl-Q`) to return
to the normal shell.

## Functions

| Function | Effect |
|----------|--------|
| `open_window(player, height=1, title=None, callback_verb=None, *args)` | Enter window mode with a `height`-row top region. Optional `callback_verb` fires when the window closes. |
| `window_write(player, row, col, text)` | Place `text` (Rich markup allowed) at `(row, col)` in the top region. |
| `window_cursor(player, row, col)` | Move the top-region cursor (for `window_emit`). |
| `window_emit(player, text)` | Write `text` at the cursor and advance it (newlines wrap to column 0). |
| `window_clear(player, row=None)` | Clear the whole top region, or a single `row`. |
| `window_split(player, height)` | Resize the top region to `height` rows. |
| `close_window(player)` | Leave window mode and return to the scrolling shell. |
| `window_supported(player)` | `True` if the player's client can display a window (rich mode). |

`window_write(player, row, col, text)` is the same as `window_cursor` followed
by `window_emit` — use whichever fits. Coordinates are zero-based; the top
region is `height` rows tall and as wide as the terminal.

## Painting the top region

The top region is a grid you set by coordinate. Recompute and repaint it
whenever the underlying state changes — for example, on every move:

```python
from moo.sdk import context, window_clear, window_write

def repaint_status(player, hp, score, moves):
    window_clear(player)
    window_write(player, 0, 0, f"[bold]HP[/bold] {hp}   Score {score}   Moves {moves}")
```

Colour and styling use the same `[tag]...[/tag]` markup as `print()` elsewhere
in the MOO; `quiet_mode` strips colour for accessibility automatically.

## Client support

| Client | Behaviour |
|--------|-----------|
| Rich (prompt_toolkit over SSH) | Full split-screen layout. |
| GMCP-capable MUD client (e.g. Mudlet) | Receives a `Window.*` GMCP package (`Window.Open`, `Window.Cell`, `Window.Cursor`, `Window.Text`, `Window.Clear`, `Window.Split`, `Window.Close`) so it can render a native status area. |
| Plain line-based client | Window calls are a no-op; the game stays fully playable in the normal scrolling shell. |

Always gate the full-screen path on `window_supported(player)` so line-based
clients fall back cleanly.

## Notes

- Window mode is **mutually exclusive** with the editor and paginator. A verb
  that tries to open one while a window is active is rejected with a notice in
  the scroll region.
- The scrolling region shows the most recent output that fits; it is not a
  scrollback pager.

For the internals — how the window Application is launched, how output is
rerouted into it, and how it tears down — see
{doc}`../explanation/shell-internals`.
