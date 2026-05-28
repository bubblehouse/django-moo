# -*- coding: utf-8 -*-
"""
Useful global utilities.
"""


def _make_access(instance, rule, permission_id, group):
    from .models.acl import Access

    return Access(
        object=instance if instance.kind == "object" else None,
        verb=instance if instance.kind == "verb" else None,
        property=instance if instance.kind == "property" else None,
        rule=rule,
        permission_id=permission_id,
        type="group",
        group=group,
    )


def apply_default_permissions(instance):
    """
    Apply default permissions to a newly created Object, Verb, or Property.

    This mirrors the logic of the ``set_default_permissions`` verb natively,
    avoiding verb-lookup and execution overhead. The verb is considered stable
    for the lifetime of a running service; changes to it require a matching
    update here and a service restart.
    """
    from .models.acl import Access, _get_permission_id

    anything_id = _get_permission_id("anything")
    perm_for_everyone = _get_permission_id("execute" if instance.kind == "verb" else "read")
    Access.objects.bulk_create(
        [
            _make_access(instance, "allow", anything_id, "wizards"),
            _make_access(instance, "allow", anything_id, "owners"),
            _make_access(instance, "allow", perm_for_everyone, "everyone"),
        ]
    )


def apply_default_permissions_bulk(instances):
    """
    Apply default permissions to many newly created instances in a single query.
    Equivalent to calling :func:`apply_default_permissions` for each instance,
    but emits only one ``INSERT`` for all ACL records combined.
    """
    from .models.acl import Access, _get_permission_id

    anything_id = _get_permission_id("anything")
    read_id = _get_permission_id("read")
    execute_id = _get_permission_id("execute")
    records = []
    for instance in instances:
        perm_for_everyone = execute_id if instance.kind == "verb" else read_id
        records.extend(
            [
                _make_access(instance, "allow", anything_id, "wizards"),
                _make_access(instance, "allow", anything_id, "owners"),
                _make_access(instance, "allow", perm_for_everyone, "everyone"),
            ]
        )
    if records:
        Access.objects.bulk_create(records)


def expand_wildcard(name):
    if "*" not in name:
        return [name]
    prefix, suffix = name.split("*", 1)
    result = [prefix]
    for i in range(len(suffix)):
        result.append(prefix + suffix[: i + 1])
    return result


def flush_attribute_caches():
    """
    Evict the cross-process verb- and property-lookup caches from Redis.

    The ``moo:verb:*`` and ``moo:prop:*`` keys cache inheritance-resolved
    lookups (verb PK sets / property values) for ``MOO_ATTRIB_CACHE_TTL``
    seconds. An object's own entries are evicted on write, but a descendant's
    cached lookup is not — so after a bulk ``moo_init --sync`` that adds or
    relocates verbs/properties on an ancestor, descendants can serve stale
    lookups until the TTL expires. Flushing gives ``--sync`` an immediate
    refresh across the long-running shell and celery processes without a
    restart.

    The per-process ``_cached_compile`` lru_cache is deliberately left alone:
    it is keyed by verb source text, so changed source yields a new key and a
    fresh compile automatically.

    No-op when the attribute cache is disabled (``MOO_ATTRIB_CACHE_TTL == 0``,
    e.g. tests) or the active cache backend is not Redis.

    :returns: the number of keys deleted.
    """
    from django.conf import settings
    from django.core.cache import cache

    if getattr(settings, "MOO_ATTRIB_CACHE_TTL", 120) == 0:
        return 0
    try:
        client = cache._cache.get_client(None)  # pylint: disable=protected-access
    except (AttributeError, NotImplementedError):
        return 0
    deleted = 0
    for namespace in ("moo:verb:", "moo:prop:"):
        pattern = cache.make_key(namespace) + "*"
        for key in client.scan_iter(match=pattern):
            client.delete(key)
            deleted += 1
    return deleted
