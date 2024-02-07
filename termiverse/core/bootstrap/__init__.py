import importlib.resources

def get_source(filename, dataset='default'):
    ref = importlib.resources.files('termiverse.core.bootstrap') / f'{dataset}_verbs/{filename}'
    with importlib.resources.as_file(ref) as path:
        with open(path) as f:
            return f.read()

def load_python(python_path):
    """
    Execute a provided Python bootstrap file against the provided database.
    """
    exec(compile(open(python_path).read(), python_path, 'exec'), globals(), dict())
