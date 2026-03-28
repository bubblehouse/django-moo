# Command Parser Reference

For a conceptual overview of how command parsing works — command forms, the BNF grammar, and lexer behavior — see {doc}`../explanation/parser`.

## Parser

Once the command has been broken up into parts by the Lexer, the Parser class assigns meaning and defines further useful attributes. For any provided object reference, the Parser will attempt to resolve the name of the object in the context of the current `caller` object.

1. Iterate through the `prepositions` object and resolve each object reference, if it can be found
2. Resolve the direct object reference, if it exists.

Once created, the Parser object has all the instance attributes of the Lexer, plus the following additions:

* `caller` - user who invoked the parser
* `dobj` - the direct object, if it can be found
* `prepositions[prep][2]` - the object of the preposition, if it can be found

> [**[TODO](https://gitlab.com/bubblehouse/django-moo/-/issues/6)**] Having thus broken the string into words, the server next checks to see if the first word names any of the six "built-in" commands: `.program`, `PREFIX`, `OUTPUTPREFIX`, `SUFFIX`, `OUTPUTSUFFIX`, or the connection's defined flush command, if any (`.flush` by default). The first one of these is only available to programmers, the next four are intended for use by client programs, and the last can vary from database to database or even connection to connection; all six are described in the final chapter of this document, "Server Commands and Database Assumptions". If the first word isn't one of the above, then we get to the usual case: a normal MOO command.

Before invoking the built-in parser, `interpret()` checks whether the system object (object #1) defines a verb named `do_command`. If it does, that verb is called with the tokenized command words passed as positional `args` and the raw command line accessible via `context.parser.command`. If `do_command` returns a truthy value, the command is considered fully handled and normal dispatch is skipped. If it returns a falsy value (or does not exist), parsing continues as described below.

The final step is to find the verb specified as the first word of the command string. `parser.get_verb()` runs the verb search, and saves the following variables in the Parser instance:

* `verb` - the verb found by the Parser, if it can be found
* `this` - the object on which the verb was found, if applicable.

### Finding an Object

One of the most common tasks of the Parser is to find an object in the context of the `caller`, aka the user who has entered the command. All `Object` instances define `obj.find(name)` and that will be the main function used to resolve strings.

1. If `spec` is "my", search the player's inventory for the name
2. If `spec` is a possessive, search the target's contents for the name
3. Otherwise `Object.find()` to search the player's location
  1. uses a case-insensitive match of the object name
  2. also searches for case-insensitive Aliases
  3. if nothing is found, `Object.find()` to search the player's inventory
4. If no object was found,
  1. ...but the string is "here", return the location.
  2. ...but the string is "me", return the player.
  3. ...but the string is a number starting with '#', return that Object by ID

### Preposition Synonym Groups

Prepositions are defined in `settings.PREPOSITIONS` as a list of synonym groups. Words within a group are interchangeable — the parser normalises them all to the first word in the group when it stores the parsed result. This means players can type `take sword using tongs` or `take sword with tongs` and both reach the same verb with the same preposition key.

| Canonical | Synonyms |
|-----------|----------|
| `with` | `using` |
| `at` | `to` |
| `in front of` | |
| `in` | `inside`, `into`, `within` |
| `on top of` | `on`, `onto`, `upon`, `above` |
| `out of` | `from inside`, `from` |
| `over` | |
| `through` | |
| `under` | `underneath`, `beneath`, `below` |
| `around` | `round` |
| `between` | `among` |
| `behind` | `past` |
| `beside` | `by`, `near`, `next to`, `along` |
| `for` | `about` |
| `is` | |
| `as` | |
| `off` | `off of` |

Verb authors should use the canonical (first) form in `--ispec` shebang options and in parser API calls such as `get_pobj_str("with")`. Any synonym also works transparently if passed directly to these methods.

### Finding a Verb

Once all the objects are defined, the caller's context is searched for the verb in the following order:

1. The caller
2. Any objects in the caller's inventory
3. The location of the caller
4. The direct object, if any
5. The objects of the preposition, if any

For each of these objects in turn, it tests if all of the the following are true:

1. `caller` can `read` object
2. object or an ancestor defines verb with a matching name

> Every verb has one or more names; all of the names are kept in a single string, separated by spaces. In the simplest case, a verb-name is just a word made up of any characters other than spaces and stars (i.e., "" and "*"). In this case, the verb-name matches only itself; that is, the name must be matched exactly.
>
> If the name contains a single star, however, then the name matches any prefix of itself that is at least as long as the part before the star. For example, the verb-name `foo*bar` matches any of the strings `foo`, `foob`, `fooba`, or `foobar`; note that the star itself is not considered part of the name.
>
> If the verb name ends in a star, then it matches any string that begins with the part before the star. For example, the verb-name `foo*` matches any of the strings `foo`, `foobar`, `food`, or `foogleman`, among many others. As a special case, if the verb-name is `*` (i.e., a single star all by itself), then it matches anything at all.

#### Last Match Wins

The search iterates through all candidate objects in the order listed above and **overwrites** `parser.this` on each match. The final match in the search order is the one that executes. This is the "last match wins" rule.

**Consequence for `--dspec any` or `--dspec this` verbs on `$player`**: if both the caller (the player who typed the command) and the direct object are `$player` instances — or both inherit the same verb from a common ancestor — then the direct object wins, because it appears later in the search order. Inside the executing verb:

- `this` = the **direct object** (not the caller)
- `context.player` = the **caller** (the player who typed the command)

```
@gag Player   →   this = Player (dobj), context.player = Wizard (caller)
page Player   →   this = Player (dobj), context.player = Wizard (caller)
```

Always use `context.player` to identify who initiated a command. Only use `this` when the verb is specifically designed to act on the object it was dispatched on (e.g., a room's `accept` verb or an exit's `go` verb).
