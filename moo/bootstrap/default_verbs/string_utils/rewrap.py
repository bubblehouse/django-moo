#!moo verb rewrap --on $string_utils

# pylint: disable=return-outside-function,undefined-variable

"""
Reflow a block of text for terminal display.

Takes a string, collapses whitespace gremlins within each paragraph (tabs,
carriage returns, non-breaking spaces, multiple spaces), removes single
newlines that interrupt paragraph flow, then wraps each paragraph to 80
characters.

Double newlines (blank lines) are treated as paragraph separators and
preserved.

Usage (as a method verb):
    result = _.string_utils.rewrap(some_text)
"""

import re

text = args[0]

# Normalise line endings first
text = re.sub(r"\r\n|\r", "\n", text)

# Collapse whitespace gremlins (tabs, non-breaking spaces, etc.) to a
# single space — but leave newlines alone so paragraph detection works
text = re.sub(r"[\t\x0b\x0c\xa0\ufeff]+", " ", text)

# Collapse runs of spaces (but not newlines)
text = re.sub(r"[ ]{2,}", " ", text)

# Split on paragraph breaks (two or more newlines)
paragraphs = re.split(r"\n{2,}", text)

wrapped_paragraphs = []
for para in paragraphs:
    # Collapse single newlines within the paragraph into spaces
    para = re.sub(r"\n", " ", para).strip()
    if not para:
        continue

    # Word-wrap to 80 characters
    words = para.split(" ")
    lines = []
    current = ""
    for word in words:
        if not word:
            continue
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= 80:
            current = current + " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    wrapped_paragraphs.append("\n".join(lines))

return "\n\n".join(wrapped_paragraphs)
