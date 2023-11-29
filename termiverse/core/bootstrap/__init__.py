import pkg_resources as pkg

def get_source(filename, dataset='default'):
    verb_path = pkg.resource_filename('termiverse.core.bootstrap', '%s_verbs/%s' % (dataset, filename))
    with open(verb_path) as f:
        return f.read()

def load_python(python_path):
    """
    Execute a provided Python bootstrap file against the provided database.
    """
    exec(compile(open(python_path).read(), python_path, 'exec'), globals(), dict())
