#!moo verb @opacity opacity --on $container --dspec this --ispec is:any

# pylint: disable=return-outside-function,undefined-variable

"""
Opacity determines when/if you can look at the contents of the container. There are three levels of opacity:

    0 - transparent
    1 - opaque
    2 - black hole

When the opacity is set to 0, you can see the contents when the pipe is open or closed. When the opacity is set to 1,
you can only see the contents when the container is open. If opacity is set to 2, you can never see the contents when
looking at the container.

The syntax for `@opacity' is:

    @opacity container is #

where '#' is either 0, 1 or 2.
"""

opacity = args[0] if args else api.parser.get_pobj_str("is")
if opacity not in ("0", "1", "2"):
    raise ValueError("Opacity must be 0, 1 or 2.")
this.set_opaque(int(opacity))
