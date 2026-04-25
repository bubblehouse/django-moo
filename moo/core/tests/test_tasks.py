# pylint: disable=no-value-for-parameter,protected-access  # Celery task decorator hides positional args from pylint
import logging
import warnings
import pytest

from django.core.cache import cache

from .. import code, tasks
from ..models import Object, Verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_simple_async_verb(t_init: Object, t_wizard: Object, caplog: pytest.LogCaptureFixture):
    printed = []

    def _writer(msg):
        printed.append(msg)

    v = t_wizard.add_verb(
        "test-async-verbs",
        code="""\
from moo.sdk import context, invoke
counter = 1
if args and len(args):
    counter = args[0] + 1
print(counter)
if counter < 10:
    verb = context.caller.get_verb("test-async-verbs")
    invoke(counter, verb=verb)
""",
        direct_object="any",
    )
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
    t_wizard.add_verb(
        "test-async-verb",
        code="""\
from moo.sdk import context, invoke
counter = 1
if args and len(args):
    counter = args[0] + 1
if counter < 10:
    return counter
""",
        direct_object="this",
    )
    t_wizard.add_verb(
        "test-async-verb-callback",
        code="""\
print(args[0])
""",
        direct_object="this",
    )

    verb = Verb.objects.get(names__name="test-async-verb")
    callback = Verb.objects.get(names__name="test-async-verb-callback")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with caplog.at_level(logging.INFO, "moo.core.tasks.background"):
            tasks.invoke_verb(
                caller_id=t_wizard.pk,
                this_id=verb.origin.pk,
                verb_name=verb.name(),
                callback_verb_name=callback.name(),
                callback_this_id=callback.origin.pk,
            )
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


# ---------------------------------------------------------------------------
# published_events tracking (input_prompt / editor / paginator events emitted
# during a parse_command task are recorded in a per-task list and exposed to the
# shell via the Django cache, keyed by the Celery task id).
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_publish_to_player_records_event_when_context_tracks(t_init: Object, t_wizard: Object):
    """_publish_to_player appends the event type to ``published_events`` when the context opts in."""
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with code.ContextManager(t_wizard, lambda _: None, track_events=True):
            _publish_to_player(t_wizard, {"event": "input_prompt", "prompt": "ok"})
            tracked = code.ContextManager.get("published_events")
            assert tracked == ["input_prompt"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_publish_to_player_skips_recording_when_context_untracked(t_init: Object, t_wizard: Object):
    """_publish_to_player does not raise when ``published_events`` is None (default)."""
    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with code.ContextManager(t_wizard, lambda _: None):
            # track_events defaults to False → published_events is None.
            _publish_to_player(t_wizard, {"event": "input_prompt", "prompt": "ok"})
            assert code.ContextManager.get("published_events") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_publish_to_player_closes_channel(t_init: Object, t_wizard: Object):
    """
    The channel acquired from the pooled connection must be closed after each
    publish; otherwise it leaks back to the broker and eventually exhausts
    the per-connection channel pool.
    """
    from unittest.mock import MagicMock, patch

    from moo.core import _publish_to_player  # pylint: disable=import-outside-toplevel

    fake_channel = MagicMock()
    fake_conn = MagicMock()
    fake_conn.channel.return_value = fake_channel
    conn_cm = MagicMock()
    conn_cm.__enter__.return_value = fake_conn
    conn_cm.__exit__.return_value = False

    fake_producer = MagicMock()
    producer_cm = MagicMock()
    producer_cm.__enter__.return_value = fake_producer
    producer_cm.__exit__.return_value = False

    from moo.celery import app  # pylint: disable=import-outside-toplevel

    original_broker = app.conf.broker_url
    app.conf.broker_url = "redis://fake"  # bypass the memory:// short-circuit
    try:
        with patch.object(app, "default_connection", return_value=conn_cm):
            with patch.object(app, "producer_or_acquire", return_value=producer_cm):
                with code.ContextManager(t_wizard, lambda _: None):
                    _publish_to_player(t_wizard, {"event": "input_prompt", "prompt": "ok"})
    finally:
        app.conf.broker_url = original_broker

    fake_channel.close.assert_called_once()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_command_writes_events_to_cache(t_init: Object, t_wizard: Object):
    """parse_command stashes published event types under ``moo:task_events:{task_id}`` in the cache."""
    from moo.core.models import verb  # noqa: F401  pylint: disable=unused-import,import-outside-toplevel

    v = t_wizard.add_verb(
        "test-emits-input",
        code="""\
from moo.sdk import open_input, context
this_verb = context.caller.get_verb("test-emits-input")
open_input(context.caller, "prompt: ", this_verb)
""",
    )
    v.owner = t_wizard
    v.save()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = tasks.parse_command.apply(args=[t_wizard.pk, "test-emits-input"])
    try:
        events = cache.get(f"moo:task_events:{result.id}")
        assert events == ["input_prompt"]
    finally:
        cache.delete(f"moo:task_events:{result.id}")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_parse_command_no_events_leaves_cache_empty(t_init: Object, t_wizard: Object):
    """parse_command writes an empty list when the verb publishes no events."""
    v = t_wizard.add_verb(
        "test-emits-nothing",
        code="""\
print("hello")
""",
    )
    v.owner = t_wizard
    v.save()

    result = tasks.parse_command.apply(args=[t_wizard.pk, "test-emits-nothing"])
    try:
        events = cache.get(f"moo:task_events:{result.id}")
        assert events == [] or events is None
    finally:
        cache.delete(f"moo:task_events:{result.id}")
