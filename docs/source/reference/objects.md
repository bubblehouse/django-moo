# Objects in the DjangoMOO Database

`Object` is a Django model representing every entity in the world:
rooms, players, items, exits, and the system object itself. Each
Object has a primary key (the LambdaMOO-style `#N` identifier), a name,
an owner, optional parents and a location, and arbitrary properties
and verbs.

This page covers the model's intrinsic attributes, public methods,
and placement API. For the conceptual model of how parent inheritance
feeds into verb and property lookup, see {doc}`caching`.

## Identity and lifecycle

Object PKs are assigned at creation and never reused. A new Object
exists in the database only after `create()` (or `Object.objects.create()`
from non-sandbox code). `@recycle` removes an Object — its PK will not be
reused.

`obj.save()` is required after changing intrinsic fields (`name`,
`unique_name`, `obvious`, `owner`). `set_property()` saves its own
row; you do not need to call `save()` after it.

`Object.delete()` (which `@recycle` calls) walks the full inherited
verb chain looking for a `recycle` verb and runs the first match.
That means a subclass's `recycle` fires automatically — `$daemon`,
`$npc`, and `$wanderer` all rely on this to disable their scheduled
ticks and drop their anonymous `Player` rows before the row is
removed.

## Fundamental attributes

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. autoattribute:: Object.pk

    The unique identifying number of this Object.

.. autoattribute:: Object.name
   :no-index:
.. autoattribute:: Object.unique_name
   :no-index:
.. autoattribute:: Object.obvious
   :no-index:
.. autoattribute:: Object.owner
   :no-index:
.. autoattribute:: Object.parents
   :no-index:
.. autoattribute:: Object.location
   :no-index:
.. autoattribute:: Object.aliases

    :class:`Alias` instances giving this object additional names.

.. autoattribute:: Object.contents

    QuerySet of objects whose ``location`` is this object — i.e. what's
    inside this room or this container.

.. autoattribute:: Object.children

    QuerySet of objects that have this object as a parent.

.. autoattribute:: Object.placement_prep
   :no-index:
.. autoattribute:: Object.placement_target
   :no-index:
```

## Inheritance

Objects can have multiple parents. Property and verb lookup walks the
parent chain in depth-then-weight order, materialised through the
`AncestorCache` denormalised table for cheap dispatch. See
{doc}`caching` for the lookup architecture and the relationship-weight
semantics.

## Methods

### Identity and traversal

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. automethod:: Object.find
.. automethod:: Object.contains
.. automethod:: Object.is_a
.. automethod:: Object.is_named
```

### Hierarchy

```{eval-rst}
.. automethod:: Object.get_ancestors
.. automethod:: Object.get_descendents
.. automethod:: Object.get_contents
.. automethod:: Object.remove_parent
```

### Verbs

```{eval-rst}
.. automethod:: Object.add_verb
.. automethod:: Object.invoke_verb
.. automethod:: Object.get_verb
.. automethod:: Object.has_verb
```

### Properties

```{eval-rst}
.. automethod:: Object.set_property
.. automethod:: Object.get_property
.. automethod:: Object.has_property
.. automethod:: Object.get_property_objects
```

### Roles and permissions

```{eval-rst}
.. automethod:: Object.is_player
.. automethod:: Object.is_wizard
.. automethod:: Object.is_connected
.. automethod:: Object.owns
.. automethod:: Object.is_allowed
```

`can_caller(permission)` is also available on every Object (inherited
from `AccessibleMixin`); it answers "would the current
`context.caller` succeed in performing `<permission>` on this object?"
without actually performing the operation. See
{doc}`../how-to/permissions` for when to reach for it (and when not
to — most verb code should just attempt the operation and let
`AccessError` propagate).

## Placement

Objects can be placed in a spatial relationship to another object in
the same room. Placement is stored as two fields:

- `placement_prep` — a preposition string (`"on"`, `"under"`,
  `"behind"`, `"before"`, `"beside"`, `"over"`).
- `placement_target` — the Object the placement is relative to.

The full set of valid prepositions is `PLACEMENT_PREPS`, and the
hidden subset (`"under"`, `"behind"`) is `HIDDEN_PLACEMENT_PREPS`.
Both are importable from `moo.sdk`. Hidden-placement objects are
invisible in the room contents listing and unfindable by name through
the parser; they can only be revealed by `look under <target>` or
`look behind <target>`.

Visible placements (`on`, `before`, `beside`, `over`) appear grouped
under their surface in the room contents:

```
On the desk: a coffee cup.
```

Placement is cleared automatically when an object is taken, dropped,
or moved. If the placement target is deleted, the database `SET_NULL`
clears the `placement_target` FK and `Object.delete()` clears the
dangling `placement_prep` on every placed child.

### Placement API

```{eval-rst}
.. py:currentmodule:: moo.core.models
.. automethod:: Object.set_placement
.. automethod:: Object.clear_placement
.. automethod:: Object.is_placed
.. automethod:: Object.is_hidden_placement
.. autoattribute:: Object.placement

    Read-only property. Returns ``(prep, target)`` tuple, or ``None``
    if not placed.
```

### Restricting valid placements

Set the `surface_types` property on a target to limit which
prepositions it accepts:

```python
desk.set_property("surface_types", ["on", "beside"])
# "place book on desk" succeeds; "place book under desk" fails.
```

If `surface_types` is absent, all placement prepositions are accepted.

## Players and avatars

A `Player` row links a Django `User` to its avatar Object via
`Player.avatar`. The Player record also carries the `wizard` boolean
that gates `is_wizard()` checks. The user-facing player is the avatar
Object — `Player` itself is plumbing for authentication and role.

To find an avatar from a username, query the `Player` model from
non-sandbox code, or call `lookup("<player name>")` from verb code.

## Built-in classes

The `default` bootstrap installs a small hierarchy of generic classes
as direct children of `$root_class`. Every game object in `default`
inherits from one of these, and your own creations should too. Each
class is also stored as a property on the System Object (`_`) for
convenient `$name` shorthand in verb shebangs (`--on $thing`).

| Class | System alias | Use for | Notable verbs |
|-------|--------------|---------|---------------|
| Generic Thing | `$thing` | Movable items players can take, drop, or place | `take`, `drop`, `look`, `place`, `examine` |
| Generic Room | `$room` | Locations players occupy | `look`, `look_self`, `accept`, `confunc`, `enterfunc`, `exitfunc` |
| Generic Exit | `$exit` | Connections between rooms (`go north`) | `go`, `move` |
| Generic Container | `$container` | Things that hold other things | `accept`, contents listing |
| Generic Player | `$player` | Connected human players (everyday commands) | `say`, `look`, `tell`, `inventory`, `@password`, `a11y`, `WRAP` |
| Generic Builder | `$builder` | World-building player class | `@create`, `@dig`, `@describe`, `@alias`, `@burrow` |
| Generic Programmer | `$programmer` | Verb-authoring player class | `@edit`, `@eval`, `@reload` |
| Generic Wizard | `$wizard` | Administrative player class | `@version`, `@npc`, `@daemon`, anything else requiring full rights |
| Generic Daemon | `$daemon` | Scheduled-tick actors with no player presence | `enable`, `disable`, `trigger`, `tick`, `on_tick`, `recycle` |
| Generic NPC | `$npc` | Autonomous, parser-visible characters | inherits from `$player` *and* `$daemon`; `act` is the personality hook |
| Generic Wanderer | `$wanderer` | NPC that moves between rooms on a tick | `act` (overrides `$npc.act`) plus `wander_rooms`, `wander_leave_msg`, `wander_arrive_msg` |

The player-class chain (`$player` → `$builder` → `$programmer` →
`$wizard`) is cumulative — `$wizard` inherits every verb attached to
`$player`. Place each new player-facing verb on the lowest class that
should be allowed to use it.

`$daemon`, `$npc`, and `$wanderer` are covered in detail in
{doc}`../how-to/npcs-and-daemons`. The relevant lifecycle for verb
authors:

- `$daemon` carries `interval`, `periodic_task_id`, `tick_count`,
  `last_tick_at`, and `target`. Override the `on_tick` verb on a
  subclass to define what happens each cycle. `enable`/`disable`
  toggle a `django_celery_beat.PeriodicTask` row through
  {func}`~moo.sdk.invoke` ``(periodic=True)`` and
  {func}`~moo.sdk.cancel_scheduled_task`. `recycle` walks inherited
  verbs to disable the schedule before deletion.
- `$npc` has two parents (`$player` for parser identity and
  `tell()`/`look_self`/gender, `$daemon` for scheduling). Its
  `on_tick` calls `this.act()`; subclasses override `act` to decide
  movement, speech, or idling.
- `$wanderer` keeps `wander_rooms` (a list of room PKs); its `act`
  override teleports to a random destination and broadcasts the
  `wander_leave_msg` / `wander_arrive_msg` strings in the
  `$player.tell` format (with `%N` substituted for the NPC's name).
