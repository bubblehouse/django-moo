"""
This class provides some useful functions related to the use of locks for objects in the database. The default database
supports a simple but powerful notation for specifying locks on objects, notes, and other applications. The idea is to
describe a constraint that must be satisfied concerning what some object must be or contain in order to use some other
object.

The constraint is given in the form of a logical expression, made up of object numbers connected with the operators
`and`, `or`, and `not` (written `&&`, `||`, and `!`).

These logical expressions (called key expressions) are always evaluated in the context of some particular candidate
object, to see if that object meets the constraint. To do so, we consider the candidate object, along with every object
it contains (and the ones those objects contain, and so on), to be `True` and all other objects to be `False`.

As an example, suppose the player `blip` wanted to lock the exit leading to his home so that only he and the holder of
his `magic wand` could use it. Further, suppose that blip was object #999 and the wand was #1001. blip would use the
`@lock` command to lock the exit with the following key expression:

    me || magic wand

and the system would understand this to mean

    #999 || #1001

That is, players could only use the exit if they were (or were carrying) either #999 or #1001.

There is one other kind of clause that can appear in a key expression:

    ? object

This is evaluated by testing whether the given object is unlocked for the candidate object; if so, this clause is true,
and otherwise, it is false. This allows you to have several locks all sharing some single other one; when the other one
is changed, all of the locks change their behavior simultaneously.

The internal representation of key expressions is stored in the property .key on every object.
"""
