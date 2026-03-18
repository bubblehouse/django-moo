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
