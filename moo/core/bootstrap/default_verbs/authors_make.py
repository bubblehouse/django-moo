#!moo verb make --on "author class" --ability

from moo.core import api, create
if not(api.parser.has_dobj_str()):
    print('[yellow]What do you want to make?[/yellow]')
    return  # pylint: disable=return-outside-function  # type: ignore

name = api.parser.get_dobj_str()
new_obj = create(name)
print('Created %s' % new_obj)
