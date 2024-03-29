"""
Parse command strings sent by the client.

This parser can understand a variety of phrases, but they are all represented
by the (BNF?) form:

<verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

There are a long list of prepositions supported, some of which are interchangeable.
"""

import re
import logging

from django.db.models.query import QuerySet

from .models import Object
from .exceptions import *  # pylint: disable=wildcard-import

log = logging.getLogger(__name__)

# Here are all our supported prepositions
preps = [['with', 'using'],
        ['at', 'to'],
        ['in front of'],
        ['in', 'inside', 'into', 'within'],
        ['on top of', 'on', 'onto', 'upon', 'above'],
        ['out of', 'from inside', 'from'],
        ['over'],
        ['through'],
        ['under', 'underneath', 'beneath', 'below'],
        ['around', 'round'],
        ['between', 'among'],
        ['behind', 'past'],
        ['beside', 'by', 'near', 'next to', 'along'],
        ['for', 'about'],
        #['is'],
        ['as'],
        ['off', 'off of']]

prepstring = "|".join(sum(preps, []))

PREP_SRC = r'(?:\b)(?P<prep>' + prepstring + r')(?:\b)'
SPEC = r"(?P<spec_str>my|the|a|an|\S+(?:\'s|s\'))"
PHRASE_SRC = r'(?:' + SPEC + r'\s)?(?P<obj_str>.+)'

PREP = re.compile(PREP_SRC)
PHRASE = re.compile(PHRASE_SRC)
POBJ_TEST = re.compile(PREP_SRC + r"\s" + PHRASE_SRC)
MULTI_WORD = re.compile(r'((\"|\').+?(?!\\).\2)|(\S+)')

def parse(caller, sentence):
    """
    For a given user, execute a command.
    """
    l = Lexer(sentence)
    p = Parser(l, caller)
    v = p.get_verb()
    v.execute(p)

class Lexer:
    """
    An instance of this class will identify the various parts of a imperitive
    sentence. This may be of use to verb code, as well.
    """
    def __init__(self, command):
        self.command = command

        self.dobj_str = None
        self.dobj_spec_str = None

        # First, find all words or double-quoted-strings in the text
        iterator = re.finditer(MULTI_WORD, command)
        self.words = []
        qotd_matches = []
        for wordmatch in iterator:
            if(wordmatch.group(1)):
                qotd_matches.append(wordmatch)
            word = wordmatch.group().strip('\'"').replace("\\'", "'").replace("\\\"", "\"")
            self.words.append(word)

        # Now, find all prepositions
        iterator = re.finditer(PREP, command)
        prep_matches = []
        for prepmatch in iterator:
            prep_matches.append(prepmatch)

        #this method will be used to filter out prepositions inside quotes
        def nonoverlap(match):
            (start, end) = match.span()
            for word in qotd_matches:
                (word_start, word_end) = word.span()
                if(word_start <= start < word_end):
                    return False
                elif(word_start < end < word_end):
                    return False
            return True

        #nonoverlap() will leave only true non-quoted prepositions
        prep_matches = list(filter(nonoverlap, prep_matches))

        #determine if there is anything after the verb
        if(len(self.words) > 1):
            #if there are prepositions, we only look for direct objects
            #until the first preposition
            if(prep_matches):
                end = prep_matches[0].start()-1
            else:
                end = len(command)
            #this is the phrase, which could be [[specifier ]object]
            dobj_phrase = command[len(self.words[0]) + 1:end]
            match = re.match(PHRASE, dobj_phrase)
            if(match):
                result = match.groupdict()
                self.dobj_str = result['obj_str'].strip('\'"').replace("\\'", "'").replace("\\\"", "\"")
                if(result['spec_str']):
                    self.dobj_spec_str = result['spec_str'].strip('\'"').replace("\\'", "'").replace("\\\"", "\"")
                else:
                    self.dobj_spec_str = ''

        self.prepositions = {}
        #iterate through all the prepositional phrase matches
        for index in range(len(prep_matches)):  # pylint: disable=consider-using-enumerate
            start = prep_matches[index].start()
            #if this is the last preposition, then look from here until the end
            if(index == len(prep_matches) - 1):
                end = len(command)
            #otherwise, search until the next preposition starts
            else:
                end = prep_matches[index + 1].start() - 1
            prep_phrase = command[start:end]
            phrase_match = re.match(POBJ_TEST, prep_phrase)
            if not(phrase_match):
                continue

            result = phrase_match.groupdict()

            #if we get a quoted string here, strip the quotes
            result['obj_str'] = result['obj_str'].strip('\'"').replace("\\'", "'").replace("\\\"", "\"")

            if(result['spec_str'] is None):
                result['spec_str'] = ''

            #if there is already a entry for this preposition, we turn it into
            #a list, and if it already is one, we append to it
            if(result['prep'] in self.prepositions):
                prep = self.prepositions[result['prep']]
                if not(isinstance(prep[0], list)):
                    self.prepositions[result['prep']] = [[result['spec_str'], result['obj_str'], None], prep]
                else:
                    self.prepositions[result['prep']].append([result['spec_str'], result['obj_str'], None])
            #if it's a new preposition, we just save it here.
            else:
                self.prepositions[result['prep']] = [result['spec_str'], result['obj_str'], None]

    def get_details(self):
        return dict(
            command            = self.command,
            dobj_str        = self.dobj_str,
            dobj_spec_str    = self.dobj_spec_str,
            words            = self.words,
            prepositions    = self.prepositions,
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
        self.dobj_str = ''
        self.dobj_spec_str = ''

        if(self.lexer):
            for key, value in list(self.lexer.get_details().items()):
                self.__dict__[key] = value

            for prep_record_list in self.prepositions.values():
                if not(isinstance(prep_record_list[0], list)):
                    prep_record_list = [prep_record_list]
                for record in prep_record_list:
                    #look for an object with this name/specifier
                    obj = self.find_object(record[0], record[1])
                    #try again (maybe it just looked like a specifier)
                    if(not obj and record[0]):
                        record[1] = record[0] + ' ' + record[1]
                        record[0] = ''
                        obj = self.find_object(record[0], record[1])
                    #one last shot for pronouns
                    if not(obj):
                        obj = self.get_pronoun_object(record[1])
                    record[2] = obj

        if(hasattr(self, 'dobj_str') and self.dobj_str):
            #look for an object with this name/specifier
            self.dobj = self.find_object(self.dobj_spec_str, self.dobj_str)
            #try again (maybe it just looked like a specifier)
            if(not self.dobj and self.dobj_spec_str):
                self.dobj_str = self.dobj_spec_str + ' ' + self.dobj_str
                self.dobj_spec_str = ''
                self.dobj = self.find_object(None, self.dobj_str)
            #if there's nothing with this name, then we look for
            #pronouns before giving up
            if not(self.dobj):
                self.dobj = self.get_pronoun_object(self.dobj_str)
        else:
            #didn't find anything, probably because nothing was there.
            self.dobj = None
            self.dobj_str = None

    def get_environment(self):
        """
        Return a dictionary of environment variables supplied by the parser results.
        """
        return dict(
            parser            = self,

            command            = self.command,
            caller            = self.caller,
            dobj            = self.dobj,
            dobj_str        = self.dobj_str,
            dobj_spec_str    = self.dobj_spec_str,
            words            = self.words,
            prepositions    = self.prepositions,
            this            = self.this,
            self            = self.verb,

            system            = Object.objects.get(pk=1),
            here            = self.caller.location if self.caller else None,

            get_dobj        = self.get_dobj,
            get_dobj_str    = self.get_dobj_str,
            has_dobj        = self.has_dobj,
            has_dobj_str    = self.has_dobj_str,

            get_pobj        = self.get_pobj,
            get_pobj_str     = self.get_pobj_str,
            has_pobj         = self.has_pobj,
            has_pobj_str     = self.has_pobj_str,
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

        if(specifier == 'my'):
            search = self.caller
        elif(specifier and specifier.find("'") != -1):
            person = specifier[0:specifier.index("'")]
            location = self.caller.location
            if(location):
                search = location.find(person)
        else:
            search = self.caller.location

        if isinstance(search, QuerySet):
            if len(search) > 1:
                raise AmbiguousObjectError(name, search)
            search = search[0]
        if(name and search):
            result = search.find(name)

        if len(result) == 1:
            return result[0]
        elif(return_list):
            return result
        elif(not result):
            return None
        raise AmbiguousObjectError(name, result)

    def get_verb(self):
        """
        Determine the most likely verb for this sentence. There is a search
        order for verbs, as follows::

            Caller->Caller's Contents->Location->Items in Location->
            Direct Object->Objects of the Preposition
        """
        if not(self.words):
            raise NoSuchVerbError('parser: ' + self.command)

        if(getattr(self, 'verb', None) is not None):
            return self.verb

        verb_str = self.words[0]
        matches = []

        checks = [self.caller]
        checks.extend(self.caller.contents.all())

        location = self.caller.location
        if(location):
            checks.append(location)
            checks.extend(location.contents.all())

        checks.append(self.dobj)

        for prep in self.prepositions.values():
            # if there were multiple uses of a preposition
            if(isinstance(prep[0], list)):
                # then check each one for a verb
                checks.extend([pobj[2] for pobj in prep if pobj[2]])
            else:
                checks.append(prep[2])

        matches = [x for x in checks if x and x.has_verb(verb_str)]
        self.this = self.filter_matches(matches)
        if(isinstance(self.this, list)):
            if(len(self.this) > 1):
                raise AmbiguousVerbError(verb_str, self.this)
            if(len(self.this) == 0):
                self.this = None
            else:
                self.this = self.this[0]

        if not(self.this):
            raise NoSuchVerbError('parser: ' + verb_str)

        #print "Verb found on: " + str(self.this)
        self.verb = self.this.get_verb(self.words[0], recurse=True)
        return self.verb

    def filter_matches(self, selection):
        result = []
        # print "selection is " + str(selection)
        verb_str = self.words[0]
        for possible in selection:
            if(possible in result):
                continue
            verb = possible.get_verb(verb_str)
            if verb.ability and possible != self.caller:
                continue
            # if not self.caller.is_allowed('execute', verb):
            #     continue
            result.append(possible)
        # print "result is " + str(result)
        return result

    def get_pronoun_object(self, pronoun):
        """
        Also, a object number (starting with a #) will
        return the object for that id.
        """
        if(pronoun == "me"):
            return self.caller
        elif(pronoun == "here"):
            return self.caller.location
        elif(pronoun[0] == "#"):
            return Object.objects.get(int(pronoun[1:]))
        else:
            return None

    def get_dobj(self):
        """
        Get the direct object for this parser. If there was no
        direct object found, raise a NoSuchObjectError
        """
        if not(self.dobj):
            raise NoSuchObjectError(self.dobj_str)
        return self.dobj

    def get_pobj(self, prep):
        """
        Get the object for the given preposition. If there was no
        object found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not(prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        if(isinstance(self.prepositions[prep][0], list)):
            matches = []
            for item in self.prepositions[prep]:
                if(item[2]):
                    matches.append(item[2])
            if(len(matches) > 1):
                raise AmbiguousObjectError(matches[0][1], matches)
            if not(matches):
                raise NoSuchObjectError(self.prepositions[prep][0][1])
        if not(self.prepositions[prep][2]):
            raise NoSuchObjectError(self.prepositions[prep][1])
        return self.prepositions[prep][2]

    def get_dobj_str(self):
        """
        Get the direct object **string** for this parser. If there was no
        direct object **string** found, raise a NoSuchObjectError
        """
        if not(self.dobj_str):
            raise NoSuchObjectError('direct object')
        return self.dobj_str

    def get_pobj_str(self, prep, return_list=False):
        """
        Get the object **string** for the given preposition. If there was no
        object **string** found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not(prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        if(isinstance(self.prepositions[prep][0], list)):
            matches = []
            for item in self.prepositions[prep]:
                if(item[1]):
                    matches.append(item[1])
            if(len(matches) > 1):
                if(return_list):
                    return matches
                else:
                    raise matches[0]
            elif not(matches):
                raise NoSuchObjectError(self.prepositions[prep][0][1])
        return self.prepositions[prep][1]

    def get_pobj_spec_str(self, prep, return_list=False):
        """
        Get the object **specifier** for the given preposition. If there was no
        object **specifier** found, return the empty string; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not(prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        if(isinstance(self.prepositions[prep][0], list)):
            matches = []
            for item in self.prepositions[prep]:
                matches.append(item[0])
            if(len(matches) > 1):
                if(return_list):
                    return matches
                else:
                    return matches[0]
        return self.prepositions[prep][0]

    def has_dobj(self):
        """
        Was a direct object found?
        """
        return self.dobj is not None

    def has_pobj(self, prep):
        """
        Was an object for this preposition found?
        """
        if(prep not in self.prepositions):
            return False

        found_prep = False

        if(isinstance(self.prepositions[prep][0], list)):
            for item in self.prepositions[prep]:
                if(item[2]):
                    found_prep = True
                    break
        else:
            found_prep = bool(self.prepositions[prep][2])
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
        if(prep not in self.prepositions):
            return False

        found_prep = False

        if(isinstance(self.prepositions[prep][0], list)):
            for item in self.prepositions[prep]:
                if(item[1]):
                    found_prep = True
                    break
        else:
            found_prep = bool(self.prepositions[prep][1])
        return found_prep