# -*- coding: utf-8 -*-
"""
Server administration and diagnostic functions.
"""


def server_info():
    """
    Return a dict with server version and process statistics.

    Keys: ``version``, ``python``, ``pid``, ``memory_mb`` (may be ``None``
    on platforms where ``resource`` is unavailable).

    :rtype: dict
    """
    import sys
    import os
    from django.conf import settings

    info = {
        "version": getattr(settings, "VERSION", "unknown"),
        "python": sys.version.split()[0],
        "pid": os.getpid(),
        "memory_mb": None,
    }
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        info["memory_mb"] = round(usage.ru_maxrss / 1024, 1)
    except Exception:  # pylint: disable=broad-except
        pass
    return info
