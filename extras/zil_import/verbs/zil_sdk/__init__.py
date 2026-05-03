"""
ZIL SDK — component verbs loaded onto the $zil_sdk object.

These verbs implement generic ZIL intrinsics called by translated verb code
via ``_.zil_sdk.FUNCTION(args)``.  They are not imported as a Python module;
they are loaded by ``load_verbs`` and dispatched through the normal DjangoMOO
verb-execution path.
"""
