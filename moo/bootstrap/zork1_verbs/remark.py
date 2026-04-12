#!moo verb remark --on $zork_thing
# pylint: disable=undefined-variable
# ZIL ACTION stub generated from dungeon.zil / actions.zil
# Original routine head: ['ROUTINE', 'REMARK', ('REMARK', 'D', 'W', 'AUX', ('LEN', ['GET', '.REMARK', 0]), ('CNT', 0), 'STR'), ['REPEAT', (), ['COND', (['G?', ['SET', 'CNT', ['+', '.CNT', 1]], '.LEN'], ['RETURN'])], ['SET', 'STR', ['GET', '.REMARK', '.CNT']], ['COND', (['EQUAL?', '.STR', 'F-WEP'], ['PRINTD', '.W']), (['EQUA...
# TODO: implement this action routine
print(f"[{verb_name}] not yet implemented.")
