"""
Parse command strings sent by the client.

This parser can understand a variety of phrases, but they are all represented
by the (BNF?) form:

<verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

There are a long list of prepositions supported, some of which are interchangeable.
"""

import logging
import re

from django.conf import settings
from django.db.models.query import QuerySet

from .exceptions import *  # pylint: disable=wildcard-import
from .models import Object, Verb

log = logging.getLogger(__name__)


def interpret(line):
    """
    For a given user, execute a command.
    """
    from . import api, code

    lex = Lexer(line)
    parser = Parser(lex, api.caller)
    api.parser = parser
    verb = parser.get_verb()
    globals = code.get_default_globals()  # pylint: disable=redefined-builtin
    globals.update(code.get_restricted_environment(api.writer))
    filename = verb.filename or "<string>"
    globals["__file__"] = filename
    code.r_exec(verb.code, {}, globals, filename=filename)


def unquote(s):
    return s.strip("'\"").replace("\\'", "'").replace('\\"', '"')


class Pattern:
    PREP_SRC = r"(?:\b)(?P<prep>" + "|".join(sum(settings.PREPOSITIONS, [])) + r")(?:\b)"
    SPEC = r"(?P<spec_str>my|the|a|an|\S+(?:\'s|s\'))"
    PHRASE_SRC = r"(?:" + SPEC + r"\s)?(?P<obj_str>.+)"
    PREP = re.compile(PREP_SRC)
    PHRASE = re.compile(PHRASE_SRC)
    POBJ_TEST = re.compile(PREP_SRC + r"\s" + PHRASE_SRC)
    MULTI_WORD = re.compile(r"((\"|\').+?(?!\\).\2)|(\S+)")

    @classmethod
    def initializePrepositions(cls):
        from .models import Preposition

        for preps in settings.PREPOSITIONS:
            preposition = Preposition.objects.create()
            for name in preps:
                preposition.names.create(name=name)

    def tokenize(self, s):
        """
        Find all words or double-quoted-strings in the text
        """
        iterator = re.finditer(self.MULTI_WORD, s)
        words = []
        qotd_matches = []
        for wordmatch in iterator:
            if wordmatch.group(1):
                qotd_matches.append(wordmatch)
            word = unquote(wordmatch.group())
            words.append(word)
        return words, qotd_matches


class Lexer:
    """
    An instance of this class will identify the various parts of a imperative
    sentence. This may be of use to verb code, as well.
    """

    def __init__(self, command):
        self.command = command

        self.dobj_str = None
        self.dobj_spec_str = None

        pattern = Pattern()
        self.words, qotd_matches = pattern.tokenize(command)

        # Now, find all prepositions
        iterator = re.finditer(pattern.PREP, command)
        prep_matches = []
        for prepmatch in iterator:
            prep_matches.append(prepmatch)

        # this method will be used to filter out prepositions inside quotes
        def nonoverlap(match):
            start, end = match.span()
            for word in qotd_matches:
                word_start, word_end = word.span()
                if word_start <= start < word_end:
                    return False
                elif word_start < end < word_end:
                    return False
            return True

        # nonoverlap() will leave only true non-quoted prepositions
        prep_matches = list(filter(nonoverlap, prep_matches))

        # determine if there is anything after the verb
        if len(self.words) > 1:
            # if there are prepositions, we only look for direct objects
            # until the first preposition
            if prep_matches:
                end = prep_matches[0].start() - 1
            else:
                end = len(command)
            # this is the phrase, which could be [[specifier ]object]
            dobj_phrase = command[len(self.words[0]) + 1 : end]
            match = re.match(pattern.PHRASE, dobj_phrase)
            if match:
                result = match.groupdict()
                self.dobj_str = unquote(result["obj_str"])
                if result["spec_str"]:
                    self.dobj_spec_str = unquote(result["spec_str"])
                else:
                    self.dobj_spec_str = ""

        self.prepositions = {}
        # iterate through all the prepositional phrase matches
        for index in range(len(prep_matches)):  # pylint: disable=consider-using-enumerate
            start = prep_matches[index].start()
            # if this is the last preposition, then look from here until the end
            if index == len(prep_matches) - 1:
                end = len(command)
            # otherwise, search until the next preposition starts
            else:
                end = prep_matches[index + 1].start() - 1
            prep_phrase = command[start:end]
            phrase_match = re.match(pattern.POBJ_TEST, prep_phrase)
            if not (phrase_match):
                continue

            result = phrase_match.groupdict()

            # if we get a quoted string here, strip the quotes
            result["obj_str"] = unquote(result["obj_str"])

            if result["spec_str"] is None:
                result["spec_str"] = ""

            self.prepositions.setdefault(result["prep"], []).append([result["spec_str"], result["obj_str"], None])

    def get_details(self):
        return dict(
            command=self.command,
            dobj_str=self.dobj_str,
            dobj_spec_str=self.dobj_spec_str,
            words=self.words,
            prepositions=self.prepositions,
        )


class Parser:  # pylint: disable=too-many-instance-attributes
    """
    The parser instance is created by the avatar. A new instance is created
    for each command invocation.
    """

    def __init__(self, lexer, caller):
        """
        Create a new parser object for the given command, as issued by
        the given caller, using the registry.
        """
        self.lexer = lexer
        self.caller = caller

        self.this = None
        self.verb = None
        self.prepositions = {}
        self.command = None
        self.words = []
        self.dobj_str = ""
        self.dobj_spec_str = ""

        if self.lexer:
            for key, value in list(self.lexer.get_details().items()):
                self.__dict__[key] = value

            for matches in self.prepositions.values():
                for record in matches:
                    spec, name, _ = record
                    # look for an object with this name/specifier
                    obj = self.find_object(spec, name)
                    # try again (maybe it just looked like a specifier)
                    if not obj and spec:
                        name = f"{spec} {name}"
                        spec = ""
                        obj = self.find_object(spec, name)
                    # one last shot for pronouns
                    if not (obj):
                        obj = self.get_pronoun_object(name)
                    record[2] = obj
        if hasattr(self, "dobj_str") and self.dobj_str:
            # look for an object with this name/specifier
            self.dobj = self.find_object(self.dobj_spec_str, self.dobj_str)
            # try again (maybe it just looked like a specifier)
            if not self.dobj and self.dobj_spec_str:
                dobj = self.find_object(None, self.dobj_spec_str + " " + self.dobj_str)
                if dobj:
                    # if we found an object, then correct the saved strings
                    self.dobj_str = self.dobj_spec_str + " " + self.dobj_str
                    self.dobj_spec_str = ""
                    self.dobj = dobj
            # if there's nothing with this name, then we look for
            # pronouns before giving up
            if not (self.dobj):
                self.dobj = self.get_pronoun_object(self.dobj_str)
        else:
            # didn't find anything, probably because nothing was there.
            self.dobj = None
            self.dobj_str = None

    def get_environment(self):
        """
        Return a dictionary of environment variables supplied by the parser results.
        """
        return dict(
            parser=self,
            command=self.command,
            caller=self.caller,
            dobj=self.dobj,
            dobj_str=self.dobj_str,
            dobj_spec_str=self.dobj_spec_str,
            words=self.words,
            prepositions=self.prepositions,
            this=self.this,
            self=self.verb,
            system=Object.objects.get(pk=1),
            here=self.caller.location if self.caller else None,
            get_dobj=self.get_dobj,
            get_dobj_str=self.get_dobj_str,
            has_dobj=self.has_dobj,
            has_dobj_str=self.has_dobj_str,
            get_pobj=self.get_pobj,
            get_pobj_str=self.get_pobj_str,
            has_pobj=self.has_pobj,
            has_pobj_str=self.has_pobj_str,
        )

    def find_object(self, specifier, name, return_list=False):
        """
        Look for an object, with the optional specifier, in the area
        around the person who entered this command. If the posessive
        form is used (i.e., "Bill's spoon") and that person is not
        here, a NoSuchObjectError is thrown for that person.
        """
        result = None
        search = None

        if specifier == "my":
            search = self.caller
        elif specifier and specifier.find("'") != -1:
            person = specifier[0 : specifier.index("'")]
            location = self.caller.location
            if location:
                search = location.find(person)
        else:
            search = self.caller.location

        if isinstance(search, QuerySet):
            if len(search) > 1:
                raise AmbiguousObjectError(name, search)
            search = search[0]
        if name and search:
            result = search.find(name)

        if len(result) == 1:
            return result[0]
        elif return_list:
            return result
        elif not result:
            return None
        raise AmbiguousObjectError(name, result)

    def get_verb(self):
        """
        Determine the most likely verb for this sentence. There is a search
        order for verbs, as follows::

            Caller->Caller's Contents->Location->
            Direct Object->Objects of the Preposition
        """
        if not (self.words):
            raise Verb.DoesNotExist(self.command)

        if getattr(self, "verb", None) is not None:
            return self.verb

        verb_str = self.words[0]
        matches = []

        checks = [self.caller]
        checks.extend(self.caller.contents.all())

        location = self.caller.location
        if location:
            checks.append(location)

        checks.append(self.dobj)

        for prep in self.prepositions.values():
            checks.extend([pobj[2] for pobj in prep if pobj[2]])

        matches = [x for x in reversed(checks) if x and x.has_verb(verb_str)]
        self.this = self.filter_matches(matches)
        if isinstance(self.this, list):
            if len(self.this) > 1:
                raise AmbiguousVerbError(verb_str, self.this)
            if len(self.this) == 0:
                self.this = None
            else:
                self.this = self.this[0]

        if not (self.this):
            raise Verb.DoesNotExist("parser: " + verb_str)

        # print "Verb found on: " + str(self.this)
        self.verb = self.this.get_verb(self.words[0])
        self.verb.invoked_name = self.words[0]
        self.verb.invoked_object = self.this
        return self.verb

    def filter_matches(self, selection):
        result = []
        verb_str = self.words[0]
        for possible in selection:
            for verb in possible.get_verb(verb_str, allow_ambiguous=True, return_first=False):
                if verb.direct_object == "this" and self.dobj != possible:
                    continue
                if verb.direct_object == "none" and self.has_dobj_str():
                    continue
                if verb.direct_object == "any" and not self.has_dobj_str():
                    continue
                for ispec in verb.indirect_objects.all():
                    for prep, values in self.prepositions.items():
                        if ispec.preposition_specifier == "none":
                            continue
                        if ispec.preposition_specifier == "this" and values[2] != possible:
                            continue
                        if ispec.preposition_specifier != "any":
                            if not ispec.preposition.names.filter(name=prep).exists():
                                continue
                # sometimes an object has multiple verbs with the same name after inheritance
                # so we need to check if the verb is already in the list
                if possible not in result:
                    result.append(possible)
        return result

    def get_pronoun_object(self, pronoun):
        """
        Also, a object number (starting with a #) will
        return the object for that id.
        """
        if pronoun == "me":
            return self.caller
        elif pronoun == "here":
            return self.caller.location
        elif pronoun[0] == "#":
            return Object.objects.get(pk=int(pronoun[1:]))
        else:
            return None

    def get_dobj(self):
        """
        Get the direct object for this parser. If there was no
        direct object found, raise a NoSuchObjectError
        """
        if not (self.dobj):
            raise Object.DoesNotExist(self.dobj_str)
        return self.dobj

    def get_pobj(self, prep):
        """
        Get the object for the given preposition. If there was no
        object found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not (prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        matches = []
        for item in self.prepositions[prep]:
            if item[2]:
                matches.append(item[2])
        if len(matches) > 1:
            raise AmbiguousObjectError(matches[0][1], matches)
        if not (matches):
            raise Object.DoesNotExist(self.prepositions[prep][0][1])
        return self.prepositions[prep][0][2]

    def get_dobj_str(self):
        """
        Get the direct object **string** for this parser. If there was no
        direct object **string** found, raise a NoSuchObjectError
        """
        if not (self.dobj_str):
            raise Object.DoesNotExist("direct object")
        return self.dobj_str

    def get_pobj_str(self, prep, return_list=False):
        """
        Get the object **string** for the given preposition. If there was no
        object **string** found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not (prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        matches = []
        for item in self.prepositions[prep]:
            if item[1]:
                matches.append(item[1])
        if len(matches) > 1:
            if return_list:
                return matches
            else:
                raise matches[0]
        elif not (matches):
            raise Object.DoesNotExist(self.prepositions[prep][0][1])
        return self.prepositions[prep][0][1]

    def get_pobj_spec_str(self, prep, return_list=False):
        """
        Get the object **specifier** for the given preposition. If there was no
        object **specifier** found, return the empty string; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not (prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        matches = []
        for item in self.prepositions[prep]:
            matches.append(item[0])
        if len(matches) > 1:
            if return_list:
                return matches
            else:
                return matches[0]
        return self.prepositions[prep][0][0]

    def has_dobj(self):
        """
        Was a direct object found?
        """
        return self.dobj is not None

    def has_pobj(self, prep):
        """
        Was an object for this preposition found?
        """
        if prep not in self.prepositions:
            return False

        found_prep = False

        for item in self.prepositions[prep]:
            if item[2]:
                found_prep = True
                break
        return found_prep

    def has_dobj_str(self):
        """
        Was a direct object string found?
        """
        return self.dobj_str is not None

    def has_pobj_str(self, prep):
        """
        Was a object string for this preposition found?
        """
        if prep not in self.prepositions:
            return False

        found_prep = False

        for item in self.prepositions[prep]:
            if item[1]:
                found_prep = True
                break
        return found_prep
