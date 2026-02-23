#!moo verb tell_contents --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
This verb displays the contents of the container. If the container is empty, the message `It is empty' is displayed.
"""

if this.contents.exists():
    print("Contents:")
    for item in this.contents.all():
        print("  " + item.title())
else:
    print("It is empty.")
