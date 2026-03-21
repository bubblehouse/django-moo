"""
Parse command strings sent by the client.

This parser can understand a variety of phrases, but they are all represented
by the (BNF?) form:

<verb>[[[<dobj spec> ]<direct-object> ]+[<prep> [<pobj spec> ]<object-of-the-preposition>]*]

There are a long list of prepositions supported, some of which are interchangeable.
"""

import logging
import re

from collections import defaultdict

from django.conf import settings
from django.db.models import F, Value
from django.db.models.query import QuerySet
import more_itertools

from .exceptions import *  # pylint: disable=wildcard-import
from .models import Object, Verb

log = logging.getLogger(__name__)


def _passes_parse_filters(verb, viewed_by, parser):
    """
    Replicates Object.parse_verb() dspec/ispec filtering for a single verb.
    Returns True if the verb matches the parser's dobj/pobj constraints
    when the search-order object is `viewed_by`.
    """
    if verb.direct_object == "this" and parser.dobj != viewed_by:
        return False
    if verb.direct_object == "none" and parser.has_dobj_str():
        return False
    if verb.direct_object == "any" and not parser.has_dobj_str():
        return False
    for ispec in verb.indirect_objects.all():
        for prep, values in parser.prepositions.items():
            if ispec.preposition_specifier == "none":
                continue
            if ispec.preposition_specifier == "this" and values[2] != viewed_by:
                return False
            if ispec.preposition_specifier != "any":
                if not ispec.preposition.names.filter(name=prep).exists():
                    return False
    return True


def interpret(ctx, line):
    """
    For a given user, execute a command.
    """
    from . import context

    lex = Lexer(line)
    parser = Parser(lex, context.player)
    ctx.set_parser(parser)
    try:
        verb = parser.get_verb()
    except NoSuchVerbError:
        if context.player.location and context.player.location.has_verb("huh"):
            verb = context.player.location.get_verb("huh")
        else:
            raise
    verb()


def unquote(s):
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        s = s[1:-1]
    return s.replace("\\'", "'").replace('\\"', '"')


class Pattern:
    PREP_SRC = r"(?:\b)(?P<prep>" + "|".join(sum(settings.PREPOSITIONS, [])) + r")(?:\b)"
    SPEC = r"(?P<spec_str>my|the|a|an|[^\s\"\']\S*(?:\'s|s\'))"
    PHRASE_SRC = r"(?:" + SPEC + r"\s)?(?P<obj_str>.+)"
    PREP = re.compile(PREP_SRC)
    PHRASE = re.compile(PHRASE_SRC)
    POBJ_TEST = re.compile(PREP_SRC + r"\s" + PHRASE_SRC)
    MULTI_WORD = re.compile(r"((\"|\').+?(?!\\).\2)|(\S+)")
    PREP_CANONICAL = {name: group[0] for group in settings.PREPOSITIONS for name in group}

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

            canonical = Pattern.PREP_CANONICAL.get(result["prep"], result["prep"])
            self.prepositions.setdefault(canonical, []).append([result["spec_str"], result["obj_str"], None])


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
        self.prepositions = lexer.prepositions
        self.command = lexer.command
        self.words = lexer.words
        self.dobj_str = lexer.dobj_str
        self.dobj_spec_str = lexer.dobj_spec_str

        if self.lexer:
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
        if self.dobj_str:
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

    def find_object(self, specifier, name, return_list=False):
        """
        Look for an object, with the optional specifier, in the area
        around the person who entered this command. If the posessive
        form is used (i.e., "Bill's spoon") and that person is not
        here, a NoSuchObjectError is thrown for that person.
        """
        result = []
        search = None

        if specifier == "my":
            search = self.caller
        elif specifier and specifier.find("'") != -1:
            person = specifier[0 : specifier.index("'")]
            location = self.caller.location
            if location:
                search = location.find(person)
        else:
            search = self.caller

        if isinstance(search, QuerySet):
            if len(search) > 1:
                raise AmbiguousObjectError(name, search)
            elif len(search) == 0:
                raise NoSuchObjectError(person)
            search = search[0]
        if name and search:
            result = search.find(name)
            if not result and self.caller.location:
                result = self.caller.location.find(name)

        if len(result) == 1:
            return result[0]
        elif return_list:
            return result
        elif not result:
            return None
        raise AmbiguousObjectError(name, result)

    def get_search_order(self):
        """
        Return the canonical list of objects to search for verbs, in priority order:
        caller, inventory, location, dobj, pobj objects. Last match wins when iterated.
        """
        return list(
            filter(
                None,
                more_itertools.collapse(
                    [
                        self.caller,
                        list(self.caller.contents.prefetch_related("aliases")),
                        self.caller.location,
                        self.dobj,
                        [[x[2] for x in prep] for prep in self.prepositions.values()],
                    ]
                ),
            )
        )

    def get_verb(self):
        """
        For each of these items the parser will look for a verb using the
        following rules:

            1. For each object in the search order, look for a verb with the
               same name as the first word in the command by traversing its
               inheritance chain.
            2. For each matching verb found, check if the verb's direct object
               and indirect object specifiers match the direct object and the
               objects of the prepositions already defined in the parser.
            3. Continue until a verb is found or the end of the chain is reached.
            4. Verbs found later in the search order will take precedence
               over verbs found earlier in the search order.
        """
        if self.verb:
            return self.verb

        search_order_list = self.get_search_order()

        if getattr(settings, "MOO_BATCH_VERB_DISPATCH", False):
            winner_this, winner_verb = self._batch_get_verb(search_order_list)
            if winner_this is not None:
                self.this = winner_this
                self.verb = winner_verb
        else:
            for obj in search_order_list:
                try:
                    if verb := obj.parse_verb(self):
                        self.this = obj
                        self.verb = verb
                except NoSuchVerbError:
                    continue

        if not self.this:
            raise NoSuchVerbError(self.words[0])

        self.verb._invoked_name = self.words[0]  # pylint: disable=protected-access
        self.verb._invoked_object = self.this  # pylint: disable=protected-access
        return self.verb

    def _batch_get_verb(self, search_order_list):
        """
        Batch verb dispatch using the AncestorCache flat table.

        Issues two VALUES queries (direct + inherited) then fetches full Verb objects
        for the finalist set — typically 3 DB round-trips instead of 5-10.

        Returns (this_object, verb) for the winning match, or (None, None) if not found.
        """
        pk_to_rank = {obj.pk: i for i, obj in enumerate(search_order_list)}
        pk_to_obj = {obj.pk: obj for obj in search_order_list}
        verb_name = self.words[0]

        # Query 1: verbs defined directly on search-order objects.
        direct = list(
            Verb.objects.filter(
                origin_id__in=pk_to_rank,
                names__name=verb_name,
            )
            .values("id", "direct_object")
            .annotate(
                viewing_pk=F("origin_id"),
                depth=Value(0),
                pw=Value(0),
            )
        )

        # Query 2: verbs inherited via AncestorCache.
        inherited = list(
            Verb.objects.filter(
                origin__ancestor_descendants__descendant_id__in=pk_to_rank,
                names__name=verb_name,
            )
            .values("id", "direct_object")
            .annotate(
                viewing_pk=F("origin__ancestor_descendants__descendant_id"),
                depth=F("origin__ancestor_descendants__depth"),
                pw=F("origin__ancestor_descendants__path_weight"),
            )
        )

        # Deduplicate: for each (verb_id, viewing_pk) keep shallowest match.
        best = {}
        for row in direct + inherited:
            vp = row["viewing_pk"]
            if vp not in pk_to_rank:
                continue
            key = (row["id"], vp)
            existing = best.get(key)
            if existing is None or (row["depth"], -row["pw"]) < (existing["depth"], -existing["pw"]):
                best[key] = row

        if not best:
            return None, None

        # Query 3: fetch full Verb objects for all candidates.
        candidate_ids = list({row["id"] for row in best.values()})
        verb_map = {
            v.pk: v
            for v in Verb.objects.filter(pk__in=candidate_ids)
            .select_related("owner")
            .prefetch_related("indirect_objects__preposition__names")
        }

        # Group by (search_rank, viewing_pk), each group sorted by (depth, -pw).
        rank_viewer_verbs = defaultdict(list)
        for (verb_id, viewing_pk), row in best.items():
            rank = pk_to_rank[viewing_pk]
            rank_viewer_verbs[(rank, viewing_pk)].append((row["depth"], -row["pw"], verb_id))
        for key in rank_viewer_verbs:
            rank_viewer_verbs[key].sort()

        # Iterate in ascending rank order; last passing match wins.
        winner_this = None
        winner_verb = None
        for rank, viewing_pk in sorted(rank_viewer_verbs.keys()):
            viewed_by = pk_to_obj[viewing_pk]
            for _depth, _neg_pw, verb_id in rank_viewer_verbs[(rank, viewing_pk)]:
                v = verb_map.get(verb_id)
                if v is not None and _passes_parse_filters(v, viewed_by, self):
                    winner_this = viewed_by
                    winner_verb = v
                    break  # shallowest passing verb for this viewer

        return winner_this, winner_verb

    def get_pronoun_object(self, pronoun):
        """
        Also, a object number (starting with a #) will
        return the object for that id.
        """
        if pronoun == "me":
            return self.caller
        elif pronoun == "here":
            return self.caller.location
        elif re.fullmatch(r"#\d+", pronoun):
            return Object.objects.get(pk=int(pronoun[1:]))
        else:
            return None

    def get_dobj(self, lookup=False):
        """
        Get the direct object for this parser. If there was no
        direct object found, raise a NoSuchObjectError
        """
        if lookup and self.dobj_str is not None:
            from moo.core import lookup

            return lookup(self.dobj_str)
        if not (self.dobj):
            raise NoSuchObjectError(self.dobj_str)
        return self.dobj

    def get_pobj(self, prep, lookup=False):
        """
        Get the object for the given preposition. If there was no object found,
        raise a NoSuchObjectError; if the preposition was not found, raise a
        NoSuchPrepositionError. Synonym prepositions (e.g. "using" for "with")
        are resolved to their canonical form automatically.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
        if not (prep in self.prepositions):
            raise NoSuchPrepositionError(prep)
        matches = []
        for item in self.prepositions[prep]:
            if lookup and item[1] is not None:
                from moo.core import lookup

                matches.append(lookup(item[1]))
            elif item[2]:
                matches.append(item[2])
        if len(matches) > 1:
            raise AmbiguousObjectError(prep, matches)
        if not (matches):
            raise NoSuchObjectError(self.prepositions[prep][0][1])
        return matches[0]

    def get_dobj_str(self):
        """
        Get the direct object **string** for this parser. If there was no
        direct object **string** found, raise a NoSuchObjectError
        """
        if not (self.dobj_str):
            raise NoSuchObjectError("direct object")
        return self.dobj_str

    def get_pobj_str(self, prep, return_list=False):
        """
        Get the object **string** for the given preposition. If there was no
        object **string** found, raise a NoSuchObjectError; if the preposition
        was not found, raise a NoSuchPrepositionError. Synonym prepositions are
        resolved to their canonical form automatically.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
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
                return matches[0]
        elif not (matches):
            raise NoSuchObjectError(self.prepositions[prep][0][1])
        return self.prepositions[prep][0][1]

    def get_pobj_spec_str(self, prep, return_list=False):
        """
        Get the object **specifier** for the given preposition. If there was no
        object **specifier** found, return the empty string; if the preposition
        was not found, raise a NoSuchPrepositionError. Synonym prepositions are
        resolved to their canonical form automatically.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
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

    def has_dobj(self, lookup=False):
        """
        Was a direct object found?
        """
        return self.dobj is not None

    def has_pobj(self, prep):
        """
        Was an object for this preposition found? Synonym prepositions are
        resolved to their canonical form automatically.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
        if prep not in self.prepositions:
            return False
        for item in self.prepositions[prep]:
            if item[2]:
                return True
        return False

    def has_dobj_str(self):
        """
        Was a direct object string found?
        """
        return self.dobj_str is not None

    def has_pobj_str(self, prep):
        """
        Was a object string for this preposition found? Synonym prepositions are
        resolved to their canonical form automatically.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
        if prep not in self.prepositions:
            return False

        found_prep = False

        for item in self.prepositions[prep]:
            if item[1]:
                found_prep = True
                break
        return found_prep
