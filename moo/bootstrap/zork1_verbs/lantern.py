#!moo verb lantern --on $lamp
# pylint: disable=undefined-variable
# ZIL ACTION stub generated from dungeon.zil / actions.zil
# Original routine head: ['ROUTINE', 'LANTERN', (), ['COND', (['VERB?', 'THROW'], ['TELL', 'The lamp has smashed into the floor, and the light has gone out.', 'CR'], ['DISABLE', ['INT', 'I-LANTERN']], ['REMOVE-CAREFULLY', 'LAMP'], ['MOVE', 'BROKEN-LAMP', 'HERE']), (['VERB?', 'LAMP-ON'], ['COND', (['FSET?', 'LAMP', 'RMUNGBIT...
# TODO: implement this action routine
print(f"[{verb_name}] not yet implemented.")
