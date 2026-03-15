import pytest

from moo.sdk import create, lookup
from moo.core.models import Object


@pytest.fixture
def setup_item():
    def _setup(location: Object, name: str = "red ball") -> Object:
        system = lookup(1)
        return create(name, parents=[system.thing], location=location)
    return _setup
