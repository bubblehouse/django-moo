#!moo verb pronoun_sub --on $string_utils

# pylint: disable=return-outside-function,undefined-variable

"""
This verb is used to substitute the pronoun properties of `who` in all occurances of `%s`, `%o`, `%p`, `%r` in text.
`who` is optional, and defaults to player. Also `%n', `%d', `%i(prep)', `%t', `%%' are substituted by player, dobj,
pobj, this and % respectively. Further, `%x(propname)' is substituted by `who.propname`. Capitalised versions of each of
these are: `%S', `%O', `%P', `%R', `%N',`%D', `%I', `%T' and `%X(propname)'. The full list is given below:

Code       Property      Pronoun       Defaults
----       --------      -------       -------
%%                                    %
%s        who.ps      subjective    he, she, it
%S        who.psc     subjective    He, She, It
%o        who.po      objective     him, her, it
%O        who.poc     objective     Him, Her, It
%p        who.pp      possessive    his, her, its
%P        who.ppc     possessive    His, Her, Its
%r        who.pr      reflexive     himself, herself, itself
%R        who.prc     reflexive     Himself, Herself, Itself
%n        who.name
%N        who.name                  (capitalised)
%d        dobj.name
%D        dobj.name                 (capitalised)
%i(prep)  pobj.name
%I(prep)  pobj.name                 (capitalised)
%t        this.name
%T        this.name                 (capitalised)
%x(xyz)   who.xyz
%X(xyz)   who.xyz                   (capitalised)
"""

import re
from moo.core import context

text = args[0]
who = args[1] if len(args) > 1 else context.player
parser = context.parser # may be none

substitutions = {
    's': 'ps',
    'o': 'po',
    'p': 'pp',
    'r': 'pr',
    'n': 'name',
    'S': 'psc',
    'O': 'poc',
    'P': 'ppc',
    'R': 'prc',
    'N': 'name',
}

for match in re.finditer(r'%(\w|%)(\((\w+)\))?', text):
    result = match.group(0)
    vartype = match.group(1)
    arg = match.group(3)
    if vartype == '%':
        result = '%'
    elif vartype.lower() == 'd':
        if parser and parser.has_dobj():
            name = parser.get_dobj().title()
            result = name.capitalize() if vartype.isupper() else name
        else:
            result = f"%{vartype}"
    elif vartype.lower() == 'i' and arg:
        if parser and parser.has_pobj(arg):
            name = parser.get_pobj(arg).title()
            result = name.capitalize() if vartype.isupper() else name
        else:
            result = f"%{vartype}({arg})"
    elif vartype.lower() == 'x' and arg:
        if who.has_property(arg):
            value = who.get_property(arg)
            result = value.capitalize() if vartype.isupper() else value
        else:
            result = f"%{vartype}({arg})"
    elif vartype in substitutions:
        prop = substitutions[vartype]
        if who.has_property(prop):
            result = who.get_property(prop)
        elif prop == 'name':
            result = who.name
        else:
            # TODO: add gender_utils to handle more genders and pronouns
            result = f"%{vartype}"
    else:
        result = f"%{vartype}"
    text = text.replace(match.group(0), result)

return text
