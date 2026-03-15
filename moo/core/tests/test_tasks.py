# pylint: disable=no-value-for-parameter,protected-access  # Celery task decorator hides positional args from pylint
import logging
import warnings
import pytest

from .. import code, tasks
from ..models import Object, Verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_simple_async_verb(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    printed = []

    def _writer(msg):
        printed.append(msg)

    v = t_wizard.add_verb("test-async-verbs", code="""\
from moo.sdk import context, invoke
counter = 1
if args and len(args):
    counter = args[0] + 1
print(counter)
if counter < 10:
    verb = context.caller.get_verb("test-async-verbs")
    invoke(counter, verb=verb)
""", direct_object="any")
    v.owner = t_wizard
    v.save()

    verb = Verb.objects.get(names__name="test-async-verbs")
    verb._invoked_name = "test-async-verbs"
    verb._invoked_object = verb.origin
    with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
        with code.ContextManager(t_wizard, _writer):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                verb()
    assert printed == [1]
    counter = 1
    for line in caplog.text.split("\n"):
        # Celery just loves emitting this when using the in-memory test broker, so ignore it
        if line.endswith("Reverting to default 'localhost'"):
            continue
        if not line:
            continue
        if "succeeded in" in line:
            continue
        counter += 1
        assert line.endswith(str(counter))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_simple_async_verb_callback(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    t_wizard.add_verb("test-async-verb", code="""\
from moo.sdk import context, invoke
counter = 1
if args and len(args):
    counter = args[0] + 1
if counter < 10:
    return counter
""", direct_object="this")
    t_wizard.add_verb("test-async-verb-callback", code="""\
print(args[0])
""", direct_object="this")

    verb = Verb.objects.get(names__name="test-async-verb")
    callback = Verb.objects.get(names__name="test-async-verb-callback")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
            tasks.invoke_verb(caller_id=t_wizard.pk, this_id=verb.origin.pk, verb_name=verb.name(), callback_verb_name=callback.name(), callback_this_id=callback.origin.pk)
    counter = 0
    for line in caplog.text.split("\n"):
        # Celery just loves emitting this when using the in-memory test broker, so ignore it
        if line.endswith("Reverting to default 'localhost'"):
            continue
        if not line:
            continue
        if "succeeded in" in line:
            continue
        counter += 1
        assert line.endswith(str(counter))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_basic_rollback(t_init: Object, t_wizard: Object):
    tasks.parse_code(
        t_wizard.pk, 'from moo.sdk import create;create(name="CreatedObjectWithAUniqueName", unique_name=True)'
    )
    with pytest.raises(RuntimeError):
        tasks.parse_code(
            t_wizard.pk,
            """from moo.sdk import create
o = create(name="ErroredObjectWithAUniqueName", unique_name=True)
raise RuntimeError()
""",
        )
    Object.objects.get(name="CreatedObjectWithAUniqueName")
    with pytest.raises(Object.DoesNotExist):
        Object.objects.get(name="ErroredObjectWithAUniqueName")
