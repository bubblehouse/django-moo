"""
Zork SDK — component verbs loaded onto the $zork_sdk object.

These verbs implement ZIL intrinsics called by translated Zork 1 verb code
via ``_.zork_sdk.FUNCTION(args)``.  They are not imported as a Python module;
they are loaded by ``load_verbs`` and dispatched through the normal DjangoMOO
verb-execution path.
"""
