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

from .exceptions import (
    AmbiguousObjectError,
    NoSuchObjectError,
    NoSuchPrepositionError,
    NoSuchVerbError,
    UsageError,
)
from .models import Object, Verb

log = logging.getLogger(__name__)


def _passes_parse_filters(verb, viewed_by, parser):
    """
    Apply a verb's dspec/ispec filters against the parser's dobj/pobj
    constraints. Returns True if the verb matches when the search-order
    object is `viewed_by`.

    ispec matching is permissive: a verb declaring a preposition still
    matches a command that omits it. An ispec only constrains the command
    when its own preposition is actually present, at which point its
    `specifier` (this/any/none) is enforced.
    """
    if verb.direct_object == "this" and parser.dobj != viewed_by:
        return False
    if verb.direct_object == "none" and parser.has_dobj_str():
        return False
    if verb.direct_object == "any" and not parser.has_dobj_str():
        return False
    for ispec in verb.indirect_objects.all():
        for prep, records in parser.prepositions.items():
            # A concrete ispec only governs its own preposition; a wildcard
            # ispec (preposition_id is None) governs any present preposition.
            if ispec.preposition_id is not None:
                if prep not in {pn.name for pn in ispec.preposition.names.all()}:
                    continue
            # `this` requires the indirect object to resolve to the verb's
            # own object. Each prep maps to a list of [spec, name, obj] records.
            if ispec.specifier == "this" and not any(rec[2] == viewed_by for rec in records):
                return False
    return True


def _ispec_specificity(verb, present_preps):
    """
    Score how well a verb's declared concrete prepositions fit the
    prepositions actually used in the command. Returns (matched, missing).
    Used only to break ties among same-name verbs on the same object — it
    never rejects a verb.
    """
    declared = set()
    for ispec in verb.indirect_objects.all():
        if ispec.preposition_id is None:  # wildcard ispec — no concrete prep
            continue
        for pn in ispec.preposition.names.all():
            declared.add(pn.name)
    return len(declared & present_preps), len(declared - present_preps)


def split_command_fragments(line: str) -> list[str]:
    """
    Split *line* into independent command fragments on ``.``, ``,``, ``;``,
    and the standalone word ``THEN`` (case-insensitive).

    The splitter is intentionally conservative — only commands clearly
    composed of multiple actions get split:

    - inside quoted strings (``"..."`` / ``'...'``) and bracketed regions
      (``()``, ``[]``, ``{}``), no separator splits anything;
    - a ``.``, ``,``, or ``;`` only splits when followed by whitespace and
      an alphabetic or ``@`` continuation (so ``emote waves hello.``,
      ``@set x [1,2]``, and ``Bill's spoon`` all pass through untouched;
      ``@``-prefixed wizard verbs after a separator do split);
    - ``THEN`` only splits when it stands alone as a word.

    Empty fragments are dropped.  Lines with no separator hits round-trip
    as a single-element list.
    """
    fragments: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    bracket_depth = 0
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if in_quote:
            current.append(ch)
            if ch == in_quote and (i == 0 or line[i - 1] != "\\"):
                in_quote = None
            i += 1
            continue
        if ch in ('"', "'"):
            in_quote = ch
            current.append(ch)
            i += 1
            continue
        if ch in "([{":
            bracket_depth += 1
            current.append(ch)
            i += 1
            continue
        if ch in ")]}":
            if bracket_depth > 0:
                bracket_depth -= 1
            current.append(ch)
            i += 1
            continue
        if bracket_depth == 0 and ch in (".", ",", ";"):
            # Require ``<sep> <whitespace>+ <alpha-or-@>`` to count as a real
            # split. Trailing punctuation (``emote waves hello.``) and
            # bracketed content (``[1, 2, 3]``) pass through untouched; ``@``
            # is allowed because MOO wizard/builder verbs start with ``@``.
            j = i + 1
            while j < n and line[j] == " ":
                j += 1
            if j > i + 1 and j < n and (line[j].isalpha() or line[j] == "@"):
                frag = "".join(current).strip()
                if frag:
                    fragments.append(frag)
                current = []
                i = j
                continue
        # Standalone "then" (case-insensitive) as a fragment separator.
        if bracket_depth == 0 and ch in ("t", "T") and line[i : i + 4].lower() == "then":
            before_ok = i == 0 or not line[i - 1].isalnum()
            after_ok = i + 4 == n or not line[i + 4].isalnum()
            if before_ok and after_ok:
                frag = "".join(current).strip()
                if frag:
                    fragments.append(frag)
                current = []
                i += 4
                continue
        current.append(ch)
        i += 1
    tail = "".join(current).strip()
    if tail:
        fragments.append(tail)
    return fragments or [line]


def interpret(ctx, line):
    """
    For a given user, execute a command.

    The raw line is first split on period/comma/THEN separators (outside
    quoted spans); each fragment is dispatched as its own command, matching
    canonical adventure-game behaviour where ``take sword. kill troll.``
    runs two turns.
    """
    for fragment in split_command_fragments(line):
        _interpret_one(ctx, fragment)


def _interpret_one(ctx, line):
    """Execute a single, already-split command fragment."""
    from . import context, lookup

    lex = Lexer(line)
    parser = Parser(lex, context.player)
    ctx.set_parser(parser)

    # Give database code a chance to handle the command first (LambdaMOO $do_command).
    # If the system object defines a do_command verb and it returns a truthy value,
    # the command is considered fully handled and normal dispatch is skipped.
    system = Object.objects.get(unique_name=True, name="System Object")
    if system.has_verb("do_command"):
        do_command = system.get_verb("do_command")
        result = do_command(*parser.words)
        if result:
            return

    try:
        verb = parser.get_verb()
    except (NoSuchVerbError, NoSuchObjectError):
        # Both dispatch failures route through the room's ``huh`` hook when
        # it exists — bootstraps that define ``huh`` get a chance to
        # explain.  Without ``huh``, the original error message reaches
        # the player verbatim (NoSuchObjectError: "There is no 'lunch'
        # here." for dead dobjs; NoSuchVerbError: "I don't know how to
        # do that." for unknown verbs).
        if context.player.location and context.player.location.has_verb("huh"):
            verb = context.player.location.get_verb("huh")
        else:
            raise
    verb()

    # After every parsed command, fire the player's current room's
    # ``turnfunc`` hook (LambdaMOO ``<thing>func`` convention) when the
    # room defines one.  Rooms without a turnfunc are unaffected.
    location = context.player.location
    if location and location.has_verb("turnfunc"):
        location.invoke_verb("turnfunc")


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
        from .models import Preposition, PrepositionName

        for preps in settings.PREPOSITIONS:
            canonical = preps[0]
            existing = PrepositionName.objects.filter(name=canonical).first()
            if existing is not None:
                preposition = existing.preposition
            else:
                preposition = Preposition.objects.create()
            for name in preps:
                PrepositionName.objects.get_or_create(name=name, defaults=dict(preposition=preposition))

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


def _check_quotes(command: str) -> None:
    """
    Raise UsageError if the command contains an unclosed quoted string.

    Scans for `"` characters that are not preceded by a backslash.  If the
    count is odd the last string was never closed, and any verb that runs
    with the misquoted token will receive a name that starts with `"` —
    almost certainly a bug.
    """
    unescaped_count = sum(1 for i, ch in enumerate(command) if ch == '"' and (i == 0 or command[i - 1] != "\\"))
    if unescaped_count % 2 != 0:
        raise UsageError("Unmatched quote in command.")


class Lexer:
    """
    An instance of this class will identify the various parts of a imperative
    sentence. This may be of use to verb code, as well.
    """

    #: The full, unparsed command string the player typed.
    command: str
    #: The tokenised words from the command, preserving quoted spans.
    words: list[str]
    #: The direct-object substring, or ``None`` if the command had no
    #: direct object.
    dobj_str: str | None
    #: Any specifier on the direct object (``my``, ``the``, a possessive
    #: like ``Bill's``). Empty string if no specifier was used; ``None``
    #: if there was no direct object at all.
    dobj_spec_str: str | None
    #: Dict mapping each preposition that appeared in the command to a
    #: list of ``[spec_str, obj_str, obj]`` triples. ``obj`` is ``None``
    #: at the lexer phase; the parser fills it in during dispatch.
    prepositions: dict

    def __init__(self, command):
        self.command = command

        self.dobj_str = None
        self.dobj_spec_str = None

        _check_quotes(command)

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

    #: The :class:`Object` that issued the command (the player who typed it).
    caller: object
    #: The full, unparsed command string. Inherited from the lexer.
    command: str
    #: The tokenised words from the command. Inherited from the lexer.
    words: list[str]
    #: The direct-object substring. Inherited from the lexer.
    dobj_str: str | None
    #: Direct-object specifier. Inherited from the lexer.
    dobj_spec_str: str | None
    #: The resolved direct object as an :class:`Object`, or ``None`` if
    #: it could not be resolved or no direct object was given.
    dobj: object
    #: Dict mapping each preposition that appeared to ``[spec_str,
    #: obj_str, obj]`` triples. After parsing, ``obj`` is the resolved
    #: :class:`Object` (or ``None`` if it could not be resolved).
    prepositions: dict
    #: The :class:`Verb` selected by dispatch, set after :meth:`get_verb`
    #: runs.
    verb: object
    #: The Object the verb was matched on (last-match-wins; see
    #: :doc:`/reference/parser`).
    this: object

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
                    # look for an object with this name/specifier.
                    # Defer AmbiguousObjectError — the pobj may be a plain string
                    # (e.g. an alias name in `@alias #N as "foo"`) that the verb
                    # reads via get_pobj_str().  Raising here would prevent the verb
                    # from running at all.  Verbs that need the resolved object call
                    # get_pobj(), which will re-raise then.
                    try:
                        obj = self.find_object(spec, name)
                        # try again (maybe it just looked like a specifier)
                        if not obj and spec:
                            name = f"{spec} {name}"
                            spec = ""
                            obj = self.find_object(spec, name)
                        # one last shot for pronouns
                        if not obj:
                            obj = self.get_pronoun_object(name)
                    except AmbiguousObjectError:
                        obj = None
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
                # Exclude objects with hidden placement (under/behind) from room lookups
                # unless an explicit "from" context is present (e.g. "take key from rug").
                exclude_hidden = "from" not in self.prepositions
                result = self.caller.location.find(name, exclude_hidden_placement=exclude_hidden)

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
        winner_this, winner_verb = self._batch_get_verb(search_order_list)
        if winner_this is not None:
            self.this = winner_this
            self.verb = winner_verb

        if not self.this:
            # Verb-name exists but dobj didn't resolve: report the dobj, not the verb.
            if self.dobj_str is not None and self.dobj is None:
                if Verb.objects.filter(names__name__iexact=self.words[0]).exists():
                    raise NoSuchObjectError(self.dobj_str)
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
        # Case-insensitive lookup: bootstrap verbs are stored in a mix of
        # cases (`look`, `OUTPUTSUFFIX`, `@create`); the player should be
        # able to type any case and have it match.
        verb_name = self.words[0]

        # Query 1: verbs defined directly on search-order objects.
        direct = list(
            Verb.objects.filter(
                origin_id__in=pk_to_rank,
                names__name__iexact=verb_name,
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
                names__name__iexact=verb_name,
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

        # Group by (search_rank, viewing_pk).
        rank_viewer_verbs = defaultdict(list)
        for (verb_id, viewing_pk), row in best.items():
            rank = pk_to_rank[viewing_pk]
            rank_viewer_verbs[(rank, viewing_pk)].append((row["depth"], -row["pw"], verb_id))

        # Iterate in ascending rank order; last viewer with a passing verb wins.
        # Within a viewer, prefer the verb whose declared prepositions best fit
        # the command (most matched, fewest unused), then the shallowest match.
        present_preps = set(self.prepositions)
        winner_this = None
        winner_verb = None
        for rank, viewing_pk in sorted(rank_viewer_verbs.keys()):
            viewed_by = pk_to_obj[viewing_pk]
            best_key = None
            best_verb = None
            for depth, neg_pw, verb_id in rank_viewer_verbs[(rank, viewing_pk)]:
                v = verb_map.get(verb_id)
                if v is None or not _passes_parse_filters(v, viewed_by, self):
                    continue
                matched, missing = _ispec_specificity(v, present_preps)
                key = (-matched, missing, depth, neg_pw, verb_id)
                if best_key is None or key < best_key:
                    best_key = key
                    best_verb = v
            if best_verb is not None:
                winner_this = viewed_by
                winner_verb = best_verb

        return winner_this, winner_verb

    def get_pronoun_object(self, pronoun):
        """
        Resolve pronoun-like dobj/iobj strings to the object they refer
        to.  Called as a fallback after :meth:`find_object` fails — so
        in-scope objects always take precedence over these matches.

        Recognised forms:

        - ``me`` — the caller.
        - ``here`` — the caller's location.
        - the caller's location's name or any of its aliases — useful
          when the player is inside a vehicle/container they want to
          name directly (``disembark boat`` while inside the boat).
        - ``#N`` — the object with primary key ``N``.
        """
        if pronoun == "me":
            return self.caller
        elif pronoun == "here":
            return self.caller.location
        elif re.fullmatch(r"#\d+", pronoun):
            try:
                return Object.objects.get(pk=int(pronoun[1:]))
            except Object.DoesNotExist as exc:
                raise NoSuchObjectError(pronoun) from exc
        loc = self.caller.location
        if loc is not None:
            if pronoun.lower() == loc.name.lower() or loc.aliases.filter(alias__iexact=pronoun).exists():
                return loc
        return None

    def get_dobj(self, lookup=False):
        """
        Return the direct object as an :class:`Object`. Use this when
        the argument refers to an existing game object.

        :param lookup: if ``True``, fall back to a global
            :func:`moo.sdk.lookup` by name when no local match is found.
            Local matches always take precedence — this prevents
            ``@obvious crate`` from resolving to a faraway "wooden crate"
            when the player has their own crate in the room.
        :raises NoSuchObjectError: if the direct object string didn't
            resolve to a real object.
        """
        if self.dobj:
            return self.dobj
        if lookup and self.dobj_str is not None:
            from moo.core import lookup

            return lookup(self.dobj_str)
        raise NoSuchObjectError(self.dobj_str)

    def get_pobj(self, prep, lookup=False):
        """
        Return the indirect object for ``prep`` as an :class:`Object`.
        Synonym prepositions (e.g. ``using`` for ``with``) are resolved
        to their canonical form automatically.

        :param prep: the preposition (canonical form or any synonym).
        :param lookup: if ``True``, fall back to a global
            :func:`moo.sdk.lookup` by name when no local match is found.
        :raises NoSuchObjectError: if the indirect object string didn't
            resolve to a real object.
        :raises NoSuchPrepositionError: if ``prep`` was not present in
            the command.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
        if prep not in self.prepositions:
            raise NoSuchPrepositionError(prep)
        matches = []
        for item in self.prepositions[prep]:
            if item[2]:
                matches.append(item[2])
            elif lookup and item[1] is not None:
                from moo.core import lookup

                matches.append(lookup(item[1]))
        if len(matches) > 1:
            raise AmbiguousObjectError(prep, matches)
        if not (matches):
            raise NoSuchObjectError(self.prepositions[prep][0][1])
        return matches[0]

    def get_dobj_str(self):
        """
        Return the direct object as a raw string. Use this when the
        argument is plain text (a message, a name to create, a code
        snippet) rather than a reference to an existing game object.

        :raises NoSuchObjectError: if no direct object string was given.
        """
        if not (self.dobj_str):
            raise NoSuchObjectError("direct object")
        return self.dobj_str

    def get_pobj_str(self, prep, return_list=False):
        """
        Return the indirect object for ``prep`` as a raw string. Use this
        when the argument is plain text rather than an object reference.

        :param prep: the preposition (canonical form or any synonym).
        :param return_list: if ``True`` and multiple matches were given,
            return all of them as a list. Default returns the first.
        :raises NoSuchObjectError: if no indirect object string was
            given for this preposition.
        :raises NoSuchPrepositionError: if ``prep`` was not present in
            the command.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
        if prep not in self.prepositions:
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
        Return the specifier (``my``, ``the``, possessive form) used
        with the indirect object for ``prep``. Useful when a verb wants
        to behave differently for ``my X`` vs. plain ``X``. Returns the
        empty string if no specifier was given.

        :param prep: the preposition (canonical form or any synonym).
        :param return_list: if ``True`` and multiple matches were given,
            return all specifiers as a list.
        :raises NoSuchPrepositionError: if ``prep`` was not present in
            the command.
        """
        prep = Pattern.PREP_CANONICAL.get(prep, prep)
        if prep not in self.prepositions:
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
        Return ``True`` if the parser resolved a direct object to a
        real :class:`Object`.
        """
        return self.dobj is not None

    def has_pobj(self, prep):
        """
        Return ``True`` if the parser resolved an indirect object for
        ``prep`` to a real :class:`Object`. Synonym prepositions are
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
        Return ``True`` if a direct object string was given on the
        command line, regardless of whether it resolved to an object.
        """
        return self.dobj_str is not None

    def has_pobj_str(self, prep):
        """
        Return ``True`` if an indirect object string was given for
        ``prep``, regardless of whether it resolved to an object.
        Synonym prepositions are resolved to their canonical form
        automatically.
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

    def get_iobj(self, lookup=False):
        """Return the first indirect-object :class:`Object` found across
        any preposition in the command, or raise :class:`NoSuchObjectError`
        if none resolved.

        Use this when the calling code doesn't care which preposition was
        typed — "the indirect object, whatever its preposition is".  For
        a specific preposition, use :meth:`get_pobj` instead.
        """
        for prep in self.prepositions:
            for item in self.prepositions[prep]:
                if item[2]:
                    return item[2]
                if lookup and item[1] is not None:
                    from moo.core import lookup as _lookup

                    return _lookup(item[1])
        raise NoSuchObjectError("indirect object")

    def has_iobj(self):
        """Return ``True`` if any preposition resolved to a real object."""
        for prep in self.prepositions:
            for item in self.prepositions[prep]:
                if item[2]:
                    return True
        return False
