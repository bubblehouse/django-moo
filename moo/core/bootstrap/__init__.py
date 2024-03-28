import importlib.resources

def get_source(filename, dataset='default'):
    ref = importlib.resources.files('moo.core.bootstrap') / f'{dataset}_verbs/{filename}'
    with importlib.resources.as_file(ref) as path:
        with open(path, encoding="utf8") as f:
            return f.read()

def load_python(python_path):
    """
    Execute a provided Python bootstrap file against the provided database.
    """
    with open(python_path, encoding="utf8") as f:
        src = f.read()
        exec(  # pylint: disable=exec-used
            compile(src, python_path, 'exec'), globals(), dict()
        )
