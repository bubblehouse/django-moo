"""
A variety of error classes
"""


class UserError(Exception):
    """
    Superclass for any error that should be displayed to the player who
    triggered it. The task runner catches every ``UserError`` raised by
    a verb and renders it as a bold red line; verbs do not need to
    ``try/except`` around calls that may raise these. Subclasses
    customize the default message rendered to the player.
    """

    def __init__(self, message, data=None):
        self._message = message
        self.data = data

    def __str__(self):
        return str(self._message)

    def __repr__(self):
        data = ""
        if self.data:
            data += "\n    " + str(self.data)
        return str(self._message) + data


class UsageError(UserError):
    """
    Raise when the player invoked a verb with bad syntax or missing
    arguments. The constructor takes the message string verbatim — that
    string is what the player sees. ``raise UsageError(f"Usage: {verb_name} <target>")``
    is the conventional pattern.
    """


class AmbiguousObjectError(UserError):
    """
    Raised when a name resolves to more than one object. Default
    message: ``When you say, "<name>", do you mean <obj1>, <obj2>, or
    <obj3>?`` — the matching objects are listed by name and ``#id`` so
    the player can disambiguate.
    """

    def __init__(self, name, matches, message=None):
        self.name = name
        if message:
            result = message
        else:
            result = 'When you say, "' + self.name + '", do you mean '
            matches = list(matches)
            for index in range(len(matches)):  # pylint: disable=consider-using-enumerate
                match = matches[index]
                if index < len(matches) - 1:
                    result += ", "
                elif index == len(matches) - 1:
                    result += " or "
                result += str(match)
            result += "?"
        UserError.__init__(self, result, matches)


class AmbiguousVerbError(UserError):
    """
    Raised when verb dispatch finds more than one matching verb at the
    same object. Default message: ``More than one object defines
    "<name>": <obj1>, <obj2>, and <obj3>.``
    """

    def __init__(self, name, matches):
        self.name = name
        result = 'More than one object defines "' + self.name + '": '
        matches = list(matches)
        for match in matches:
            index = matches.index(match)
            if index < len(matches) - 1:
                result += ", "
            elif index == len(matches) - 1:
                result += " and "
            result = result + str(match)
        result = result + "."
        UserError.__init__(self, result, matches)


class AccessError(PermissionError):
    """
    Subclass of Python's ``PermissionError`` raised by model-layer
    permission checks (``Object.save()``, ``Verb.__call__()``, etc.)
    when the caller lacks the required permission. Default message:
    ``<accessor> is not allowed to '<action>' on <subject>``. The task
    runner catches ``PermissionError`` automatically.
    """

    def __init__(self, accessor, access_str, subject):
        self.subject = subject
        self.accessor = accessor
        self.access_str = access_str

        PermissionError.__init__(self, "%s is not allowed to '%s' on %s" % (str(accessor), access_str, str(subject)))


class RecursiveError(UserError):
    """
    Raised if the user attempts to put a container inside one of its contents,
    or set the parent of an object to one of its children. This is unlikely
    to happen because of user error, and may not need to be presented to the
    user, but will be for the time.
    """


class QuotaError(UserError):
    """
    Raised when ``@create`` is invoked by a player whose object quota is
    exhausted. Default message: ``You don't have enough quota to create
    that.``
    """


class NoSuchPrepositionError(UserError):
    """
    Raised by parser methods like :meth:`Parser.get_pobj_str` when the
    requested preposition was not present in the player's command.
    Default message: ``I don't understand you.``
    """

    def __init__(self, prep):
        UserError.__init__(self, "I don't understand you.", prep)


class NoSuchObjectError(UserError):
    """
    Raised when a name does not resolve to any object in scope —
    typically by :meth:`Parser.get_dobj` or :func:`moo.sdk.lookup`.
    Default message: ``There is no '<name>' here.``
    """

    def __init__(self, name):
        UserError.__init__(self, "There is no '" + str(name) + "' here.")


class NoSuchVerbError(UserError):
    """
    Raised by the parser when no verb on any candidate object matches
    the typed command. Default message: ``I don't know how to do that.``
    """

    def __init__(self, name):
        UserError.__init__(self, "I don't know how to do that.", name)


class NoSuchPropertyError(UserError):
    """
    Raised by :meth:`Object.get_property` when the named property does
    not exist on the object or any of its ancestors. Default message:
    ``There is no '<name>' property defined.``
    """

    def __init__(self, name, origin=None):
        UserError.__init__(
            self, "There is no '" + str(name) + "' property defined" + [".", " on %s." % origin][bool(origin)]
        )


class ExecutionError(UserError):
    """
    Raised when user code causes some kind of exception.
    """

    def __init__(self, code, e):
        self.code = code
        self.e = e
        UserError.__init__(self, "An error occurred in user code: %s" % e)
