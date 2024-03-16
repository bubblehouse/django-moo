import logging

from .code import vars

log = logging.getLogger(__name__)

class API:
    class descriptor:
        def __init__(self, name):
            self.name = name

        def __get__(self, obj, objtype=None):
            d = vars.get({})
            return d[self.name]

        def __set__(self, obj, value):
            d = vars.get({})
            d[self.name] = value
            vars.set(d)

    caller = descriptor('caller')
    writer = descriptor('writer')
    args = descriptor('args')
    kwargs = descriptor('kwargs')
    parser = descriptor('parser')

api = API()

# TODO: make more generic, provide parser/lexer access
