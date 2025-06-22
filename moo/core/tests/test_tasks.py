import logging
import warnings
import pytest
from django.test import override_settings

from .. import code, tasks
from ..models import Object, Verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_STORE_EAGER_RESULT=True)
def test_simple_async_verb(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    printed = []

    def _writer(msg):
        printed.append(msg)

    verb = Verb.objects.get(names__name="test-async-verbs")
    with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
        with code.context(t_wizard, _writer):
            verb()
    counter = 1
    assert printed == [counter]
    for line in caplog.text.split("\n"):
        if not line:
            continue
        if "succeeded in" in line:
            continue
        counter += 1
        assert line.endswith(str(counter))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_STORE_EAGER_RESULT=True)
def test_simple_async_verb_callback(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    verb = Verb.objects.get(names__name="test-async-verb")
    callback = Verb.objects.get(names__name="test-async-verb-callback")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
            tasks.invoke_verb(caller_id=t_wizard.pk, verb_id=verb.pk, callback_verb_id=callback.pk, this_id=verb.origin.pk)
    counter = 0
    for line in caplog.text.split("\n"):
        if not line:
            continue
        if "succeeded in" in line:
            continue
        counter += 1
        assert line.endswith(str(counter))
