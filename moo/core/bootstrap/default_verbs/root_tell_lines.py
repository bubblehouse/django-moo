#!moo verb tell_lines --on "Root Class"

strings = args[1]

"""
This outputs out the list of strings strings to the object, using the tell verb for this object. Each string in strings
is output on a separate line.
"""

for arg in strings:
    this.tell(arg)
