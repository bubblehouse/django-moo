"""
The root class is the base class from which all objects are descended. It is the keystone of the database and defines
fundamental verbs and properties common to every object. If you are a programmer you can examine the properties and
verbs of the root class using the command:

    @show $root_class

You can examine the code for a verb on the class by using, for example, the following command.

    @show description on $root_class

This lists the program definition for the verb `$root_class.description`. An interesting point to note is that this
code can be changed by the owner - in this case the Wizard - to provide any functionality desired. This configurability
of the basis of the whole default database allows a large degree of flexibility in the way the DjangoMOO server is
used. It also allows for very subtle and perplexing problems. Care must be taken when editing definitions on any of the
fundamental classes, the `$root_class` in particular. However, as the base classes of the default database have been
thoroughly tested and debugged, there should be very little need for any changes by the average database administrator.
"""
