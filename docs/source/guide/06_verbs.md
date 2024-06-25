# Verbs on Objects

> The final kind of piece making up an object is verbs. A verb is a named MOO program that is associated with a particular object. Most verbs implement commands that a player might type; for example, in the LambdaCore database, there is a verb on all objects representing containers that implements commands of the form `put object in container`. It is also possible for MOO programs to invoke the verbs defined on objects. Some verbs, in fact, are designed to be used only from inside MOO code; they do not correspond to any particular player command at all. Thus, verbs in MOO are like the 'procedures' or 'methods' found in some other programming languages.
>
> As with properties, every verb has an owner and a set of permission bits. The owner of a verb can change its program, its permission bits, and its argument specifiers (discussed below). Only a wizard can change the owner of a verb. The owner of a verb also determines the permissions with which that verb runs; that is, the program in a verb can do whatever operations the owner of that verb is allowed to do and no others. Thus, for example, a verb owned by a wizard must be written very carefully, since wizards are allowed to do just about anything.

**Remember, in DjangoMOO, verbs run with the permission of the _caller_, not the original author of the verb.**

To add a new Verb to an object, users must have the `develop` permission on that object (owners and wizards get this by default). Verbs support the following permissions for any given object or object group:

* `anything` - do anything with a verb
* `read` - read the essential attributes of verb
* `write` - modify the essential attributes of a verb
* `entrust` - can change the owner of a verb
* `grant` - can set permissions on a verb
* `execute` - can run a verb

Verbs also have some attributes of their own:

1. `method` (`Boolean`) - whether this verb is callable as a method
2. `ability` (`Boolean`) - whether this object is an intrinsic ability
3. `code` (`str`) - the actual code of the verb

> In addition to an owner and some permission bits, every verb has three 'argument specifiers', one each for the direct object, the preposition, and the indirect object. The direct and indirect specifiers are each drawn from this set: `this`, `any`, or `none`. The preposition specifier is `none`, `any`, or one of the items in this list:
>
> * `with/using`
> * `at/to`
> * `in front of`
> * `in/inside/into`
> * `on top of/on/onto/upon`
> * `out of/from inside/from`
> * `over`
> * `through`
> * `under/underneath/beneath`
> * `behind`
> * `beside`
> * `for/about`
> * `is`
> * `as`
> * `off/off of`
>
> The argument specifiers are used in the process of parsing commands, described in the next chapter.

**As of yet, [DjangoMOO does not define argument specifiers on the verb itself](#5), instead allowing verbs to fetch different parts of the command string regardless of preposition.**
