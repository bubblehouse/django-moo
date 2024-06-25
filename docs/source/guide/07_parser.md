# The Built-In Command Parser

The DjangoMOO server has a fairly robust parser for handling the commands that a player enters. In particular, it can follow any imperative command that takes one of the following forms:

    verb
    verb direct-object
    verb (the|my|player's) direct-object
    verb direct-object preposition object-of-the-preposition
    verb preposition object-of-the-preposition

and many other, basically anything of the psuedo-BNF form:

    <verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

Some valid commands include:

    look
    take phil's book
    take the yellow bird
    put yellow bird in my cuckoo clock with great care

You might notice this adds a few capabilities that do not exist in the LambdaMOO parser:

* **object references can be prefixed with a specifier** - This can either be an article like `the` or a detail that helps the parser find the object, like `my` or a possessive string.
* **multiple prepositions may be used in one command** - Since [verbs are not currently fixed to a specific preposition](#5), a verb is able to parse out any of the prepositions used in a particular invocation, and raise sensible errors without additional handling.
* **intelligent tokenization** - more on this below

This area of DjangoMOO was most inspired by the parser in Twisted Reality, the MUD-like game created by Glyph and co a million years ago.

## Lexer

The first step of the command parser is the lexical analysis. We start with an intelligent tokenization process that splits the command around any known prepositions.

Once again quoting the [LambdaMOO Programmer's Manual](https://www.hayseed.net/MOO/manuals/ProgrammersManual.html):

> The server next breaks up the command into words. In the simplest case, the command is broken into words at every run of space characters; for example, the command `foo bar baz` would be broken into the words `foo`, `bar`, and `baz`. To force the server to include spaces in a "word", all or part of a word can be enclosed in double-quotes. For example, the command
>
> `foo "bar mumble" baz" "fr"otz" bl"o"rt`
>
> is broken into the words `foo`, `bar mumble`, `baz frotz`, and `blort`. Finally, to include a double-quote or a backslash in a word, they can be preceded by a backslash, just like in MOO strings.

In the DjangoMOO parser it's not usually necessary to quote the names of objects with spaces in their names. The only exception is if an object contains a defined preposition, e.g., my favorite "bag of holding".

Once created with a command string, a Lexer object has the following instance attributes:

* `command` - the full, unparsed command string
* `dobj_str` - the direct object string, if applicable
* `dobj_spec_str` - any specifier used for the direct object ("my", "the", possessives)
* `words` - the direct object string, if applicable
* `prepositions` - a map of `preposition => [spec_str, obj_str, obj]`; note the `obj` reference is `None` at this phase

The `Lexer` instance gets passed to the Parser object along with a reference to the calling user (the "caller").

## Parser

Once the command has been broken up into parts by the Lexer, the Parser class assigns meaning and defines further useful attributes. For any provided object reference, the Parser will attempt to resolve the name of the object in the context of the current `caller` object.

1. Iterate through the `prepositions` object and resolve each object reference, if it can be found
2. Resolve the direct object reference, if it exists.

Once created, the Parser object has all the instance attributes of the Lexer, plus the following additions:

* `caller` - user who invoked the parser
* `dobj` - the direct object, if it can be found
* `prepositions[prep][2]` - the object of the preposition, if it can be found

> [**[TODO](#6)**] Having thus broken the string into words, the server next checks to see if the first word names any of the six "built-in" commands: `.program`, `PREFIX`, `OUTPUTPREFIX`, `SUFFIX`, `OUTPUTSUFFIX`, or the connection's defined flush command, if any (`.flush` by default). The first one of these is only available to programmers, the next four are intended for use by client programs, and the last can vary from database to database or even connection to connection; all six are described in the final chapter of this document, "Server Commands and Database Assumptions". If the first word isn't one of the above, then we get to the usual case: a normal MOO command.

> [**[TODO](#7)**] The server next gives code in the database a chance to handle the command. If the verb `$do_command()` exists, it is called with the words of the command passed as its arguments and `argstr` set to the raw command typed by the user. If `$do_command()` does not exist, or if that verb-call completes normally (i.e., without suspending or aborting) and returns a false value, then the built-in command parser is invoked to handle the command as described below. Otherwise, it is assumed that the database code handled the command completely and no further action is taken by the server for that command.

The final step is to find the verb specified as the first word of the command string. `parser.get_verb()` runs the verb search, and saves the following variables in the Parser instance:

* `verb` - the verb found by the Parser, if it can be found
* `this` - the object on which the verb was found, if applicable.

### Finding an Object

One of the most common tasks of the Parser is to find an object in the context of the `caller`, aka the user who has entered the command. All `Object` instances define `obj.find(name)` and that will be the main function used to resolve strings.

1. If `spec` is "my", search the user's inventory for the name
2. If `spec` is a possessive, search the target's contents for the name
3. Otherwise `Object.find()` to search the caller's location
  1. uses a case-insensitive match of the object name
  2. also searches for case-insensitive Aliases
4. If no object was found,
  1. ...but the string is "here", return the location.
  2. ...but the string is "me", return the caller.
  3. ...but the string is a number starting with '#', return that Object by ID

### Finding a Verb

Once all the objects are defined, the caller's context is searched for the verb in the following order:

1. The caller
2. Any objects in the caller's inventory
3. The location of the caller
4. Any objects in the location of the caller
5. The direct object, if any
6. The objects of the preposition, if any

For each of these objects in turn, it tests if all of the the following are true:

1. `caller` can `read` object
2. object or an ancestor defines verb with a matching name
  1. if verb is an `ability`, the object must be the caller
  2. if the verb was already found on this object, skip it

> Every verb has one or more names; all of the names are kept in a single string, separated by spaces. In the simplest case, a verb-name is just a word made up of any characters other than spaces and stars (i.e., "" and "*"). In this case, the verb-name matches only itself; that is, the name must be matched exactly.
>
> [**[TODO](#8)**] If the name contains a single star, however, then the name matches any prefix of itself that is at least as long as the part before the star. For example, the verb-name `foo*bar` matches any of the strings `foo`, `foob`, `fooba`, or `foobar`; note that the star itself is not considered part of the name.
>
> If the verb name ends in a star, then it matches any string that begins with the part before the star. For example, the verb-name `foo*` matches any of the strings `foo`, `foobar`, `food`, or `foogleman`, among many others. As a special case, if the verb-name is `*` (i.e., a single star all by itself), then it matches anything at all.
