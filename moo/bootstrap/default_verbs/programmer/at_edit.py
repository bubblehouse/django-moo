#!moo verb @edit edit_callback --on $programmer --dspec any --ispec on:any

# pylint: disable=return-outside-function,undefined-variable

"""
Modify a verb or property in a full-screen editor.
The verb or property to edit is determined by the dobj of the command, and the
object to edit is determined by the pobj of the command.
"""

from moo.sdk import context, open_editor, NoSuchVerbError, NoSuchPropertyError

if verb_name == "@edit":
    attribute = context.parser.get_dobj_str()
    target = context.parser.get_pobj("on", lookup=True)
    obj = None
    try:
        obj = target.get_verb(attribute, recurse=False)
        content = obj.code
        content_type = "python"
    except NoSuchVerbError:
        pass
    try:
        obj = target.get_property(attribute, recurse=False, original=True)
        content = obj.value
        content_type = "json"
    except NoSuchPropertyError:
        pass
    if not obj:
        print(f"{attribute} is not a verb or property on {target}")
        return
    callback = this.get_verb("edit_callback")
    open_editor(context.player, content, callback, obj.pk, obj.kind, content_type=content_type, title=str(obj))
elif verb_name == "edit_callback":
    from moo.core.models.verb import Verb
    from moo.core.models.property import Property
    content = args[0]
    obj_pk = args[1]
    obj_kind = args[2]
    if obj_kind == "verb":
        obj = Verb.objects.get(pk=obj_pk)
        obj.code = content
    elif obj_kind == "property":
        obj = Property.objects.get(pk=obj_pk)
        obj.value = content
    obj.save()
