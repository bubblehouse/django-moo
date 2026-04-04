#!moo verb @edit edit_callback --on $programmer --dspec any --ispec on:any --ispec with:any

# pylint: disable=return-outside-function,undefined-variable

"""
Modify a verb or property in a full-screen editor.

Syntax:
    @edit <name> on <object> [with <content>]
    @edit verb <name> on <object> [with <content>]
    @edit property <name> on <object> [with <content>]

The verb or property to edit is determined by the dobj of the command, and the
object to edit is determined by the pobj of the "on" preposition.

If "with" is specified, the content is set directly without opening the editor.
Otherwise, the editor is opened.

Use "verb" or "property" prefix to disambiguate when an object has both.
"""

from moo.sdk import context, open_editor, NoSuchVerbError, NoSuchPropertyError, moojson

if verb_name == "@edit":
    dobj_str = context.parser.get_dobj_str()
    target = context.parser.get_pobj("on", lookup=True)

    # Parse the dobj to determine type (verb/property) and attribute name
    edit_type = None  # None = auto-detect, "verb" or "property" for explicit
    attribute = dobj_str

    if dobj_str.startswith("verb "):
        edit_type = "verb"
        attribute = dobj_str[5:]  # Remove "verb " prefix
    elif dobj_str.startswith("property "):
        edit_type = "property"
        attribute = dobj_str[9:]  # Remove "property " prefix

    # Check if "with" preposition was provided
    use_editor = not context.parser.has_pobj_str("with")
    new_content = None
    if not use_editor:
        new_content = context.parser.get_pobj_str("with")
        # Allow \n in the with-content to represent real newlines, enabling
        # multi-line verb code without the full-screen editor
        new_content = new_content.replace("\\n", "\n")
        # Repair a common LLM generation error: a bare \ before a letter that
        # isn't a recognised Python escape (e.g. \import, \from) gets treated
        # as a newline.  This turns "context\import" into "context\nimport".
        import re as _re

        new_content = _re.sub(r"\\([a-zA-Z_])", lambda m: "\n" + m.group(1), new_content)

    # Find the object to edit
    obj = None
    content = None
    content_type = None
    is_new = False

    if edit_type == "property":
        # Explicitly editing a property
        try:
            obj = target.get_property(attribute, recurse=False, original=True)
            content = obj.value
            content_type = "json"
        except NoSuchPropertyError:
            if use_editor:
                # When explicitly requesting a property without "with", require it to exist
                print(f"{attribute} is not a property on {target}")
                return
            else:
                # Create new property when using "with"
                is_new = True
                content_type = "json"
    elif edit_type == "verb":
        # Explicitly editing a verb
        try:
            obj = target.get_verb(attribute, recurse=False)
            content = obj.code
            content_type = "python"
        except NoSuchVerbError:
            if use_editor:
                # When explicitly requesting a verb without "with", require it to exist
                print(f"{attribute} is not a verb on {target}")
                return
            else:
                # Create new verb when using "with"
                is_new = True
                content_type = "python"
    else:
        # Auto-detect: try verb first, then property
        try:
            obj = target.get_verb(attribute, recurse=False)
            content = obj.code
            content_type = "python"
        except NoSuchVerbError:
            pass
        if not obj:
            try:
                obj = target.get_property(attribute, recurse=False, original=True)
                content = obj.value
                content_type = "json"
            except NoSuchPropertyError:
                pass
        if not obj:
            if use_editor:
                print(f"{attribute} is not a verb or property on {target}")
                return
            # When using "with" without explicit type, cannot determine whether to create verb or property
            print(f"{attribute} is not a verb or property on {target}. Use 'verb' or 'property' prefix to create new.")
            return

    # Either open editor or directly set content
    if use_editor:
        callback = this.get_verb("edit_callback")
        open_editor(context.player, content, callback, obj.pk, obj.kind, content_type=content_type, title=str(obj))
    else:
        # Directly set the content (same behavior as edit_callback)
        if content_type == "python":
            # Parse shebang metadata if present (sets direct_object/indirect_objects)
            import moo.bootstrap

            shebang_result = moo.bootstrap.parse_shebang(new_content)
            dspec = "none"
            ispec = None
            shebang_names = None
            if new_content.lstrip().startswith("#!moo verb") and not shebang_result:
                print(
                    "Error: malformed shebang — check --dspec (or --dobj) / --ispec (or --iobj) spelling and --on argument."
                )
                return
            if shebang_result:
                shebang_names, _, dspec, ispec = shebang_result

            # Verb: create or update with Python code
            if is_new:
                names = shebang_names if shebang_names else [attribute]
                target.add_verb(*names, code=new_content, direct_object=dspec, indirect_objects=ispec)
                print(f"Created verb {attribute} on {target}")
            else:
                from moo.core.models.verb import set_indirect_objects

                obj.code = new_content
                obj.direct_object = dspec
                set_indirect_objects(obj, ispec)
                obj.save()
                print(f"Set verb {attribute} on {target}")
        else:
            # Property: set raw JSON value (like editor does with obj.value = content)
            # The parser strips quotes, so 'with "Duff"' gives us 'Duff'
            # We need to encode it as JSON for storage
            try:
                # Try to parse as JSON - if it works, it's already valid JSON
                moojson.loads(new_content)
                json_value = new_content
            except (ValueError, TypeError):
                # Not valid JSON, treat as a string and encode it
                json_value = moojson.dumps(new_content)

            if is_new:
                # Create property with empty value, then fetch and update
                target.set_property(attribute, "")
                obj = target.get_property(attribute, recurse=False, original=True)
            # Update the raw value (either new or existing)
            obj.value = json_value
            obj.save()
            if is_new:
                print(f"Created property {attribute} on {target}")
            else:
                print(f"Set property {attribute} on {target}")
elif verb_name == "edit_callback":
    from moo.core.models.verb import Verb, set_indirect_objects
    from moo.core.models.property import Property

    content = args[0]
    obj_pk = args[1]
    obj_kind = args[2]
    if obj_kind == "verb":
        obj = Verb.objects.get(pk=obj_pk)
        obj.code = content
        # Parse shebang metadata if present
        import moo.bootstrap

        shebang_result = moo.bootstrap.parse_shebang(content)
        if content.lstrip().startswith("#!moo verb") and not shebang_result:
            print(
                "Error: malformed shebang — check --dspec (or --dobj) / --ispec (or --iobj) spelling and --on argument."
            )
            return
        if shebang_result:
            _, _, dspec, ispec = shebang_result
            obj.direct_object = dspec
            set_indirect_objects(obj, ispec)
    elif obj_kind == "property":
        obj = Property.objects.get(pk=obj_pk)
        obj.value = content
    obj.save()
