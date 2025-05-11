import pytest

from .. import code, create
from ..exceptions import QuotaError
from ..models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_create_object(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    with code.context(t_wizard, _writer):
        obj = create("widget")
    assert obj.name == "widget"
    assert obj.pk > 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_create_object_with_quota(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    t_wizard.set_property("ownership_quota", 1)
    with code.context(t_wizard, _writer):
        obj = create("widget")
        with pytest.raises(QuotaError):
            create("widget 2")
    quota = t_wizard.get_property("ownership_quota")
    assert quota == 0
    assert obj.name == "widget"
    assert obj.pk > 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_delete_object_with_quota(t_init: Object, t_wizard: Object):
    printed = []

    def _writer(msg):
        printed.append(msg)

    t_wizard.set_property("ownership_quota", 2)
    with code.context(t_wizard, _writer):
        obj = create("widget")
    quota = t_wizard.get_property("ownership_quota")
    assert quota == 1
    with code.context(t_wizard, _writer):
        obj.delete()
    quota = t_wizard.get_property("ownership_quota")
    assert quota == 2
