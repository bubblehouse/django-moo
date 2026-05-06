"""
ZIL SDK — component verbs implementing generic ZIL intrinsics.

These verbs are loaded by ``load_verbs`` and dispatched through the normal
DjangoMOO verb-execution path.  Most are attached to the System Object so
translated routines call them as ``_.flag(...)``, ``_.queue(...)``, etc.
``zstate_get`` / ``zstate_set`` live on ``$player`` (per-player state) and
``move`` lives on ``$root_class`` (any object can move another).
"""
