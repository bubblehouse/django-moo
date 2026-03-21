# How Command Parsing Works

The DjangoMOO server has a fairly robust parser for handling the commands that a player enters. In particular, it can follow any imperative command that takes one of the following forms:

    verb
    verb direct-object
    verb (the|my|player's) direct-object
    verb direct-object preposition object-of-the-preposition
    verb preposition object-of-the-preposition

and many other, basically anything of the pseudo-BNF form:

    <verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

Some valid commands include:

    look
    take phil's book
    take the yellow bird
    put yellow bird in my cuckoo clock with great care

You might notice this adds a few capabilities that do not exist in the LambdaMOO parser:

* **object references can be prefixed with a specifier** - This can either be an article like `the` or a detail that helps the parser find the object, like `my` or a possessive string.
* **multiple prepositions may be used in one command** - A verb is able to parse out any of the prepositions used in a particular invocation, and raise sensible errors without additional handling.
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

For the full reference — object resolution order, preposition synonym table, verb search order, and dispatch rules — see {doc}`../reference/parser`.
