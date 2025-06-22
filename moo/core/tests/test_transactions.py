import pytest

from .. import tasks
from ..models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_basic_rollback(t_init: Object, t_wizard: Object):
    tasks.parse_code(
        t_wizard.pk, 'from moo.core import create;create(name="CreatedObjectWithAUniqueName", unique_name=True)'
    )
    with pytest.raises(RuntimeError):
        tasks.parse_code(
            t_wizard.pk,
            """from moo.core import create
o = create(name="ErroredObjectWithAUniqueName", unique_name=True)
raise RuntimeError()
""",
        )
    Object.objects.get(name="CreatedObjectWithAUniqueName")
    with pytest.raises(Object.DoesNotExist):
        Object.objects.get(name="ErroredObjectWithAUniqueName")
