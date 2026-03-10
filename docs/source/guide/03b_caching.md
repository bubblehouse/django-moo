# Caching

django-moo uses a three-tier caching architecture to avoid redundant database queries during
verb and property lookups. The tiers are, from fastest to slowest:

1. **Session cache** — an in-process `dict` per `ContextManager`, valid for one command invocation
2. **Cross-session cache** — a Redis-backed `django.core.cache` store, shared across requests
3. **`AncestorCache` table** — a denormalized DB table that replaces recursive CTEs on the hot path

---

## Tier 1: Session cache

Each `ContextManager` instance allocates two plain dicts when it is entered:

```python
self.verb_lookup_cache = {}
self.prop_lookup_cache = {}
```

These are installed into `contextvars` (`_verb_lookup_cache`, `_prop_lookup_cache`) so they are
accessible anywhere within the current async/thread context via `ContextManager.get_verb_lookup_cache()`
and `ContextManager.get_prop_lookup_cache()`. They are reset to `None` when the `ContextManager` exits.

### Verb session cache

Key: `(object_pk, name, recurse, return_first)`
Value: the list of matching `Verb` objects, or `None` to record a confirmed miss.

`_lookup_verb()` checks this dict before touching the database. On a miss it populates the entry
after the DB query resolves. `add_verb()` evicts all affected entries when a new verb is added to
an object so the same session sees the change immediately.

### Property session cache

Key: `(object_pk, name, recurse)`
Value: the deserialized Python value, or `_PROP_MISSING` to record a confirmed miss.

`get_property()` checks this dict for non-`original` lookups (raw `Property` ORM objects are not
cached here as they carry mutable ORM state). `set_property()` evicts the relevant entries on write.

---

## Tier 2: Cross-session cache

When `MOO_ATTRIB_CACHE_TTL > 0`, results are also stored in Django's configured cache backend
(typically Redis in production). This lets warm results survive across separate requests and Celery
tasks without hitting the database.

### Configuration

```python
# settings/base.py
MOO_ATTRIB_CACHE_TTL = 120  # seconds; set to 0 to disable
```

Set `MOO_ATTRIB_CACHE_TTL = 0` in test environments (see `settings/test.py`). The in-process
`LocMemCache` does not reset between test cases, so a cached result from one test would poison
subsequent tests when database PKs are reused after sequence resets.

### Verb cross-session cache

Key: `moo:verb:<object_pk>:<name>:<recurse>:<return_first>`
Value: a comma-separated string of `Verb` PKs, e.g. `"42,17"`, or `__moo:verb:missing__` for a
confirmed miss.

PKs are stored rather than serialized `Verb` objects to avoid stale ORM state. On a cache hit,
`_lookup_verb()` re-fetches the full objects with `select_related` and `prefetch_related` in a
single query. Results are then stored in the session cache so subsequent lookups within the same
command are free.

`add_verb()` calls `cache.delete()` for all combinations of `(recurse, return_first)` flags when
a verb is created on an object, so the next lookup repopulates the cache cleanly.

### Property cross-session cache

Key: `moo:prop:<object_pk>:<name>:<recurse>`
Value: the raw moojson text of the property value, or `__moo:prop:missing__` for a confirmed miss.

Raw moojson is stored rather than a deserialized value to avoid issues serializing `Object`
references across processes. `get_property()` calls `moojson.loads()` on the cached string.

`set_property()` calls `cache.delete()` for both `recurse` variants when a property is written.
Descendant caches are intentionally *not* invalidated — they expire naturally within
`MOO_ATTRIB_CACHE_TTL`. This is an acceptable trade-off for gameplay: a brief window of staleness
on inherited properties is preferable to the cost of walking the full descendant tree on every write.

---

## Tier 3: AncestorCache table

`AncestorCache` is a denormalized flat table that replaces recursive CTEs on the hot path for
both verb and property inheritance lookups.

### Schema

```
AncestorCache(descendant_id, ancestor_id, depth, path_weight)
```

- `depth` — number of hops from descendant to ancestor (1 = direct parent)
- `path_weight` — the `Relationship.weight` of the depth-1 link leading to this ancestor;
  higher weight means higher priority when multiple inheritance paths reach the same ancestor

Indexed on `(descendant, depth, path_weight)` and `(ancestor)`.

### How it is used

`_lookup_verb()` and `get_property()` join against `ancestor_descendants` (the reverse relation
from `AncestorCache.ancestor`) rather than issuing a recursive CTE:

```python
Verb.objects.filter(
    origin__ancestor_descendants__descendant=self,
    names__name=name,
).annotate(
    ancestor_depth=F("origin__ancestor_descendants__depth"),
    path_weight=F("origin__ancestor_descendants__path_weight"),
).order_by("ancestor_depth", "-path_weight")
```

This is a single indexed JOIN rather than a recursive walk, which is significantly cheaper at
dispatch time.

### Maintenance

The table is kept consistent by the `relationship_changed()` signal, which fires on
`parents.add()` and `parents.remove()`. On any topology change, `_rebuild_ancestor_cache_for()`
deletes and recreates rows for the affected object and all its descendants. The rebuild itself
uses a recursive CTE (via `django-cte`) to compute the correct depths and weights.

To rebuild the entire table after a bulk import or data migration:

```bash
python manage.py rebuild_ancestor_cache
```

---

## Batch verb dispatch (experimental)

When `MOO_BATCH_VERB_DISPATCH = True`, the parser replaces the sequential per-object
`_lookup_verb()` loop with a single `_batch_get_verb()` call that issues two bulk queries against
`AncestorCache` — one for direct verbs, one for inherited — then fetches the winning `Verb`
objects in a third query. This reduces typical dispatch from 5–10 round-trips to 3.

```python
# settings/base.py
MOO_BATCH_VERB_DISPATCH = False  # requires AncestorCache to be populated (migration 0025)
```

This flag is off by default while the implementation is being validated against the sequential
path.

---

## Sentinels

Four sentinel objects are used to distinguish cache states:

| Name | Scope | Purpose |
|------|-------|---------|
| `_PROP_MISSING` | Session dict | Marks a confirmed property miss (distinguishes from a `None` value) |
| `_CACHE_MISS` | Cross-session cache | Returned by `cache.get()` when a key is absent; never stored |
| `_CACHE_PROP_MISSING` | Cross-session cache | Stored string marking a confirmed property miss |
| `_CACHE_VERB_MISSING` | Cross-session cache | Stored string marking a confirmed verb miss |

`_PROP_MISSING` and `_CACHE_MISS` are unique Python objects compared with `is`; the string
sentinels are serializable values stored in Redis.
