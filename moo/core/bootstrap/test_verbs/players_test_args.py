from moo.core import api

if api.parser is not None:
    print('PARSER')
elif args is not None:  # pylint: disable=undefined-variable
    print(f'METHOD:{args}:{kwargs}')  # pylint: disable=undefined-variable
