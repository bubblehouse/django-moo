#!moo verb describe --on "author class" --ability

from moo.core import api

if not(api.parser.has_dobj_str()):
    print('[yellow]What do you want to describe?[/yellow]')
    return  # pylint: disable=return-outside-function  # type: ignore
if not(api.parser.has_pobj_str('as')):
    print('[yellow]What do you want to describe that as?[/yellow]')
    return  # pylint: disable=return-outside-function  # type: ignore

subject = api.parser.get_dobj()
subject.set_property('description', api.parser.get_pobj_str('as'))
print('Description set for %s' % subject)
