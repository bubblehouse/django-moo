import pkg_resources as pkg

def get_source(filename, dataset='default'):
    verb_path = pkg.resource_filename('termiverse.core.bootstrap', '%s_verbs/%s' % (dataset, filename))
    with open(verb_path) as f:
        return f.read()
