# Database Query Optimization

One of the most common performance issues in Django applications is the N+1 query problem, where your code makes one query to get a list of objects, then makes an additional query for each object to fetch related data. DjangoMOO uses PostgreSQL and Django's ORM, so understanding query optimization is essential for building efficient verbs and administrative code.

## The N+1 Problem

Here's a common problematic pattern:

```python
# BAD: Creates N+1 queries (1 for objects, then 1 for each object's owner)
all_objects = Object.objects.all()
for obj in all_objects:
    print(f"{obj.name} owned by {obj.owner.username}")
```

This code makes 1 query to fetch all objects, then 1 additional query for each object to fetch its owner. With 100 objects, that's 101 queries!

## Using select_related()

For foreign key relationships, use `select_related()` to fetch related objects in a single query:

```python
# GOOD: Creates 2 queries (objects + owners in one batch)
all_objects = Object.objects.select_related('owner', 'location')
for obj in all_objects:
    print(f"{obj.name} owned by {obj.owner.username}")  # No additional queries!
```

`select_related()` works on:
- Foreign keys (many-to-one relationships)
- One-to-one relationships

## Using prefetch_related()

For reverse foreign key relationships (one-to-many) and many-to-many, use `prefetch_related()`:

```python
# GOOD: Prefetches all properties and verbs for each object
objects = Object.objects.prefetch_related('properties', 'verbs')
for obj in objects:
    for prop in obj.properties.all():  # No additional queries!
        print(f"Property: {prop.name}")
```

`prefetch_related()` works on:
- Reverse foreign keys (e.g., Object's properties)
- Many-to-many relationships

## Combining select_related() and prefetch_related()

In verb code or administrative functions, combine both for optimal performance:

```python
# Fetch objects with related data in minimum queries
objects = Object.objects.filter(
    location=player.location,
    visible=True
).select_related(
    'owner',
    'location'
).prefetch_related(
    'properties',
    'verbs',
    'allowed_readers',
    'allowed_writers'
)

for obj in objects:
    # All these access the pre-fetched data without additional queries
    print(obj.owner.username)
    print(obj.location.name)
    for verb in obj.verbs.all():
        print(verb.name)
```

## Query Analysis with .query

To understand what queries Django is generating, use the `.query` attribute:

```python
from django.core.management import call_command
from django.test.utils import CaptureQueriesContext
from django.db import connection

# See the SQL being generated
qs = Object.objects.all()
print(qs.query)

# Count queries in a context
with CaptureQueriesContext(connection) as queries:
    all_objects = Object.objects.all()
    for obj in all_objects:
        _ = obj.owner.username

print(f"Executed {len(queries)} queries")
for query in queries:
    print(query['sql'])
```

## Common Optimization Patterns

### Pattern 1: Getting Player's Visible Inventory

```python
"""Show what's in your inventory."""
player = api.current_player()

# Optimize: fetch all items with owners in 2 queries instead of N+1
items = Object.objects.filter(
    location=player
).select_related('owner')

if not items.exists():
    return "Your inventory is empty."

result = "You are carrying:\n"
for item in items:
    result += f"  - {item.name} (owned by {item.owner.username})\n"
return result
```

### Pattern 2: Getting Room Contents with Properties

```python
"""Get detailed contents of the current room."""
room = api.current_player().location

# Optimize: fetch objects with owner and properties
contents = Object.objects.filter(
    location=room
).select_related('owner').prefetch_related('properties')

result = f"Contents of {room.name}:\n"
for obj in contents:
    description = obj.get_property('description', 'An object')
    result += f"  - {obj.name}: {description}\n"
return result
```

### Pattern 3: Permission Checking at Scale

```python
"""Find all objects the player can modify."""
player = api.current_player()

# Optimize: fetch objects with readers/writers permissions
modifiable = Object.objects.filter(
    allowed_writers=player
).prefetch_related('allowed_readers', 'allowed_writers')

for obj in modifiable:
    if obj.can_caller('write'):  # This uses the prefetched data
        print(f"Can modify: {obj.name}")
```

## Performance in Verb Code

Since verbs have a 3-second execution time limit, efficient database access is critical. Use `select_related()` and `prefetch_related()` in all verbs that iterate over collections:

```python
# In a verb that processes many objects
# BAD: Might timeout with large object count
all_objects = Object.objects.all()
for obj in all_objects:
    location = obj.location.name  # Creates N queries!

# GOOD: Completes quickly
all_objects = Object.objects.select_related('location')
for obj in all_objects:
    location = obj.location.name  # Uses prefetched data
```

## Long-Running Operations with Celery

For operations that need to process many objects and might exceed the 3-second timeout, use `moo.core.invoke()` to execute in a Celery task:

```python
from moo.core import invoke

"""Process all objects (long operation)."""
# This creates a Celery task that runs separately
# Each task gets its own 3-second timeout
invoke("process_all_objects", this)
return "Processing in background..."
```

## Django QuerySet Methods

Useful QuerySet methods for optimization:

- **`only()`**: Fetch only specific fields (reduces memory)
  ```python
  Object.objects.only('id', 'name', 'owner_id')
  ```

- **`defer()`**: Fetch all fields except specified ones (useful for large text fields)
  ```python
  Object.objects.defer('description')  # Don't fetch description initially
  ```

- **`values()` / `values_list()`**: Return dictionaries instead of model instances (faster for read-only operations)
  ```python
  Object.objects.values_list('id', 'name')  # Returns tuples
  ```

- **`exists()`**: Check if any results exist without fetching them
  ```python
  if Object.objects.filter(owner=player).exists():
      print("Player owns objects")
  ```

- **`count()`**: Get count using database COUNT, not Python len()
  ```python
  count = Object.objects.filter(location=room).count()  # Efficient
  ```

## Database Indexes

For frequently queried fields, ensure database indexes exist. Check Django's model definitions:

```python
class Object(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    location = models.ForeignKey('Object', on_delete=models.PROTECT, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

Fields with `db_index=True` have database indexes that speed up queries.

## Testing Query Performance

In `pytest` tests, use `assertNumQueries` to ensure queries don't increase unexpectedly:

```python
from django.test import TestCase

class ObjectTestCase(TestCase):
    def test_inventory_queries_optimized(self):
        """Verify inventory listing doesn't create N+1 queries."""
        from django.test.utils import assertNumQueries

        with self.assertNumQueries(2):  # Expect exactly 2 queries
            items = Object.objects.filter(
                location=self.player
            ).select_related('owner')
            list(items)  # Force evaluation
```

## Summary

Database query optimization is crucial for DjangoMOO performance:

1. **Always use `select_related()`** for foreign key relationships
2. **Always use `prefetch_related()`** for reverse FK and M2M relationships
3. **Test with actual data** to see real-world performance
4. **Use `assertNumQueries` in tests** to prevent regression
5. **Remember the 3-second verb timeout** when processing objects
6. **Use Celery for long operations** via `invoke()`

Efficient queries mean faster verbs and better player experience!
