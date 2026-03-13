"""
Sphinx extension that makes verb files in moo.bootstrap.default_verbs importable.

Verb files use module-level ``return`` statements and bare injected variables
(``args``, ``this``, etc.) that are valid in the sandbox but cause SyntaxError
or NameError when Python tries to import them as regular modules. This extension
registers a custom MetaPathFinder/Loader pair that intercepts those imports,
wraps the source in a function body so ``ast.parse`` can handle ``return``, and
produces a synthetic module whose ``__doc__`` combines the shebang metadata
(verb name, ``--on``, ``--dspec``, ``--ispec``) with the original docstring.
"""
import sys
import ast
import argparse
import importlib.abc
import importlib.machinery
from pathlib import Path

VERB_PACKAGE = 'moo.bootstrap.default_verbs'
SHEBANG_PREFIX = '#!moo verb'


def _parse_shebang(line):
    """Parse a ``#!moo verb`` shebang line into a metadata dict."""
    rest = line[len(SHEBANG_PREFIX):].strip()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('names', nargs='*')
    parser.add_argument('--on', default=None)
    parser.add_argument('--dspec', default=None)
    parser.add_argument('--ispec', default=None)
    try:
        ns, _ = parser.parse_known_args(rest.split())
    except SystemExit:
        return {'names': [rest], 'on': None, 'dspec': None, 'ispec': None}
    return {'names': ns.names, 'on': ns.on, 'dspec': ns.dspec, 'ispec': ns.ispec}


def _format_doc(meta, original_docstring):
    """Build an RST docstring combining shebang metadata and the original docstring."""
    parts = []
    if meta['names']:
        parts.append("**Verb**: " + ', '.join(f'``{n}``' for n in meta['names']))
    if meta['on']:
        parts.append(f"**On**: ``{meta['on']}``")
    if meta['dspec']:
        parts.append(f"**dspec**: ``{meta['dspec']}``")
    if meta['ispec']:
        parts.append(f"**ispec**: ``{meta['ispec']}``")
    header = ' | '.join(parts)
    if original_docstring:
        return f"{original_docstring.strip()}\n\n{header}"
    return header


class VerbLoader(importlib.abc.Loader):
    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path

    def create_module(self, spec):
        return None  # use default module creation

    def exec_module(self, module):
        source = Path(self.path).read_text()
        lines = source.splitlines()

        shebang_line = lines[0] if lines else ''
        meta = _parse_shebang(shebang_line)

        # Wrap in a function so ast.parse accepts top-level return statements
        indented = "\n".join("    " + l for l in lines)
        wrapped = f"def _verb():\n{indented}\n"
        try:
            tree = ast.parse(wrapped)
            docstring = ast.get_docstring(tree.body[0])
        except SyntaxError:
            docstring = None

        module.__doc__ = _format_doc(meta, docstring)
        module.__file__ = self.path


class VerbFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if not fullname.startswith(VERB_PACKAGE + '.'):
            return None
        if path is None:
            return None
        module_name = fullname.rsplit('.', 1)[-1]
        for search_path in path:
            file_path = Path(search_path) / (module_name + '.py')
            if not file_path.exists():
                continue
            text = file_path.read_text()
            first_line = text.splitlines()[0] if text.strip() else ''
            if first_line.startswith(SHEBANG_PREFIX):
                loader = VerbLoader(fullname, str(file_path))
                return importlib.machinery.ModuleSpec(
                    fullname, loader, origin=str(file_path)
                )
        return None


def setup(app):
    sys.meta_path.insert(0, VerbFinder())
    return {'version': '0.1', 'parallel_read_safe': True}
