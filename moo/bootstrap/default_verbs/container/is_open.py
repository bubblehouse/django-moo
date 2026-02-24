#!moo verb is_open --on $container

# pylint: disable=return-outside-function,undefined-variable

"""
This verb checks if the container is open. It returns `True` if the container is open, and `False` otherwise.
"""

result = this.get_property("open")
return result
