class Caller:
    def __get__(self, obj, objtype=None):
        from . import code
        return code.get_caller()

class Args:
    def __get__(self, obj, objtype=None):
        from . import code
        return code.get_args()[0]

class KwArgs:
    def __get__(self, obj, objtype=None):
        from . import code
        return code.get_args()[1]

class API:
    caller = Caller()
    args = Args()
    kwargs = KwArgs()

api = API()
