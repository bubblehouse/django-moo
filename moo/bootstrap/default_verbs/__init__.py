"""
The default verbs for the DjangoMOO server, based on LambdaCore.

This package is heavily derived from the LambdaMOO and LambdaCore documentation,
including the LambdaCore Programmer's Manual and the LambdaMOO Programmer's Manual.
The verb code was written without reading the original LambdaCore source; it is
an independent reimplementation based on documented behavior and conventions.

Various verbs have been modified from their LambdaCore equivalents to better fit
a Pythonic codebase: output uses ``print()`` rather than return values, property
access follows Django ORM patterns, and permission idioms have been updated to
account for differences in how this server dispatches verbs compared to LambdaMOO.

References
----------

*LambdaCore Database User's Manual* (LambdaMOO 1.3, April 1991)
    Mike Prudence (blip), Simon Hunt (Ezeke), Floyd Moore (Phantom),
    Kelly Larson (Zaphod), Al Harrington (geezer)

*LambdaCore Programmer's Manual* (LambdaMOO 1.8.0p6, Copyright 1991)
    Mike Prudence (blip), Simon Hunt (Ezeke), Floyd Moore (Phantom),
    Kelly Larson (Zaphod), Al Harrington (geezer)

*LambdaMOO Programmer's Manual* (LambdaMOO 1.8.0p6, March 1997)
    Pavel Curtis (Haakon / Lambda)
"""
