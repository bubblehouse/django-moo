#!moo verb tell_lines --on "Root Class"

"""
This outputs out the list of strings strings to the object, using the tell verb for this object. Each string in strings
is output on a separate line.
"""

strings = args[0]

for arg in strings:
    this.tell(arg)
