"""
Parse command strings sent by the client.

This parser can understand a variety of phrases, but they are all represented
by the (BNF?) form:

<verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

There are a long list of prepositions supported, some of which are interchangeable.
"""
import logging

import spacy
from spacy import util
from spacy.tokens import Doc, Span
from spacy.matcher import Matcher

from .models import Object, Verb
from .exceptions import NoSuchPrepositionError, AmbiguousObjectError, AmbiguousVerbError

log = logging.getLogger(__name__)

def parse(caller, command):
    """
    For a given user, execute a command.
    """
    p = Parser(caller, command)
    v = p.get_verb()
    v.execute(p)

class Parser:
    """
    An instance of this class will identify the various parts of a imperitive
    sentence. This may be of use to verb code, as well.
    """
    def __init__(self, caller, command):
        self.nlp = nlp = spacy.load('en_core_web_sm')
        nlp.component('mergeTokens', func=self.merge_tokens)
        nlp.factory('objectLinker', func=self.object_linker)
        nlp.remove_pipe("ner")
        nlp.add_pipe("ner", source=spacy.load("en_core_web_sm"))
        nlp.add_pipe('mergeTokens', before="ner")
        nlp.add_pipe('objectLinker', last=True)
        self.caller = caller
        self.command = command
        self.words = nlp(command)
        self.prepositions = {}
        length = len(self.words)
        if length > 1:
            self.dobj_str = self.words[1]
        for token in self.words:
            if token.dep_ == 'prep':
                self.prepositions.setdefault(token.text, []).append(token.nbor())

    def object_linker(self, nlp, name):
        Doc.set_extension("objects", default=[], force=True)
        Span.set_extension("objects", default=[], force=True)
        def _link(doc):
            for sent in doc.sents:
                sent._.objects = []
                for token in sent:
                    if token.pos_ not in ('NOUN', 'PROPN'):
                        continue
                    cleaned, context = self.filter_reference(token)
                    found = self.get_pronoun_object(cleaned) or list(context.find(cleaned))
                    sent._.objects.extend(found)
                    doc._.objects.extend(found)
            return doc
        return _link

    def filter_reference(self, token):
        s = token.text
        parts = s.split()
        context = self.caller.location
        if s.startswith('"') and s.endswith('"'):
            s = s.strip('"')
        elif s.startswith("'") and s.endswith("'"):
            s = s.strip("'")
        elif s.startswith('my '):
            s = ' '.join(parts[1:])
            context = self.caller
        elif parts[0].endswith("'s"):
            search = parts[0][:-2]
            qs = self.caller.location.find(search)
            if len(qs) == 1:
                s = ' '.join(parts[1:])
                context = qs[0]
            elif len(qs) > 1:
                raise AmbiguousObjectError(search, qs)
        return s, context

    def merge_tokens(self, doc):
        matched_spans = []
        matcher = Matcher(self.nlp.vocab)
        matcher.add('QUOTED', [
            [{'ORTH': "'"}, {'IS_ALPHA': True, 'OP': '+'}, {'ORTH': "'"}],
            [{'ORTH': '"'}, {'IS_ALPHA': True, 'OP': '+'}, {'ORTH': '"'}],
        ])
        matcher.add('SPECIFIERS', [
            [{'ORTH': "the"}, {'POS': "NOUN"}],
            [{'ORTH': "the"}, {'POS': "PROPN"}],
            [{'ORTH': "my"}, {'POS': "NOUN"}],
            [{'ORTH': "my"}, {'POS': "PROPN"}],
        ])
        matcher.add('POSESSIVES', [
            [{'POS': "PROPN"}, {'ORTH': "'s"}, {'POS': "NOUN"}],
        ])
        matches = matcher(doc)
        for _, start, end in matches:
            span = doc[start:end]
            matched_spans.append(span)
        with doc.retokenize() as retokenizer:
            for span in util.filter_spans(matched_spans):
                retokenizer.merge(span)
        return doc

    def get_verb(self):
        """
        Determine the most likely verb for this sentence. There is a search
        order for verbs, as follows::

            Caller->Caller's Contents->Location->Items in Location->
            Direct Object->Objects of the Preposition
        """
        if not(self.words):
            raise Verb.DoesNotExist('parser: ' + self.command)
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
        if self.has_dobj_str():
            checks.extend(self.dobj_str._.objects)
        for tokens in self.prepositions.values():
            for token in tokens:
                checks.extend(token._.objects)
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
            raise Verb.DoesNotExist(verb_str)
        self.verb = self.this.get_verb(self.words[0], recurse=True)
        return self.verb

    def filter_matches(self, selection):
        result = []
        verb_str = self.words[0]
        for possible in selection:
            if(possible in result):
                continue
            verb = possible.get_verb(verb_str)
            if verb.ability and possible != self.caller:
                continue
            if not self.caller.is_allowed('execute', verb):
                continue
            result.append(possible)
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
        if not(self.dobj_str):
            raise Verb.DoesNotExist(self.dobj_str)
        matches = self.dobj_str.sent._.objects
        if len(matches) > 1:
            raise AmbiguousObjectError(self.dobj_str, matches)
        if not(matches):
            raise Object.DoesNotExist(self.dobj_str)
        return matches[0]

    def get_pobj(self, prep):
        """
        Get the object for the given preposition. If there was no
        object found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not(prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        matches = []
        for token in self.prepositions[prep]:
            matches.extend(token.sent._.objects)
        if(len(matches) > 1):
            raise AmbiguousObjectError(matches[0].text, matches)
        if not(matches):
            raise Object.DoesNotExist(self.prepositions[prep])
        return matches[0]

    def get_dobj_str(self):
        """
        Get the direct object **string** for this parser. If there was no
        direct object **string** found, raise a NoSuchObjectError
        """
        if not(self.dobj_str):
            raise Object.DoesNotExist('direct object')
        clean, _ = self.filter_reference(self.dobj_str)
        return clean

    def get_pobj_str(self, prep, return_list=False):
        """
        Get the object **string** for the given preposition. If there was no
        object **string** found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError.
        """
        if not(prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        if return_list:
            return self.prepositions[prep]
        clean, _ = self.filter_reference(self.prepositions[prep][0])
        return clean

    def has_dobj(self):
        """
        Was a direct object found?
        """
        if not self.dobj_str:
            return False
        return bool(self.dobj_str.sent._.objects)

    def has_pobj(self, prep):
        """
        Was an object for this preposition found?
        """
        if(prep not in self.prepositions):
            return False
        return bool(len(self.prepositions[prep].sent._.objects))

    def has_dobj_str(self):
        """
        Was a direct object string found?
        """
        return self.dobj_str is not None

    def has_pobj_str(self, prep):
        """
        Was an object string for this preposition found?
        """
        if(prep not in self.prepositions):
            return False
        return bool(len(self.prepositions[prep]))
