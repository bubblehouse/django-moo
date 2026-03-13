#!moo verb tell_contents --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
Display the contents of the container. If the container is empty, the message ``It is empty`` is displayed.
"""

contents = list(this.contents.all())
if contents:
    print("Contents:")
    for item in contents:
        print("  " + item.title())
else:
    print("It is empty.")
