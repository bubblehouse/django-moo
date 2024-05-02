from moo.core import api

if api.parser is not None:
    print('PARSER')
elif api.args is not None:
    print('METHOD')
else:
    print(f'parser: {api.parser}, args: {api.args}')
