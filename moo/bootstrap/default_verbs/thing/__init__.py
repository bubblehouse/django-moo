"""
The `$thing` defines verbs and properties for objects that exist in the virtual world. This class includes everything
that is not a player, room or exit. For example, the classes `$container` and `$note` are descended from the `$thing`
class. The two basic operations that can be performed on a thing are picking it up and putting it down. Two verbs are
defined for the `$thing` class to implement this idea. Configurable messages are used, so that someone using an object
of this class can set the text printed when an attempt is made to take an object.
"""
