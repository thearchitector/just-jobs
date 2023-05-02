from concurrent.futures import Executor

import pytest


def test_serialization(settings):
    payload = {"function": print, "args": set("hello world")}

    serialized = settings.job_serializer(payload)
    deserialized = settings.job_deserializer(serialized)

    assert payload == deserialized


def test_serialization_bad_signature(settings):
    payload = {"function": print, "args": set("hello world")}

    serialized = settings.job_serializer(payload)
    payloadb = serialized.split(b"|", 1)[1]
    tampered = b"invalidsignature|" + payloadb

    with pytest.raises(ValueError, match="Invalid job signature"):
        settings.job_deserializer(tampered)


async def test_lifecycle(settings, pcapture):
    context = {}

    with pcapture as target:
        await settings.on_startup(context)
        assert "_executors" in context
        assert all([isinstance(v, Executor) for v in context["_executors"].values()])

        await settings.on_shutdown(context)
        assert "_executors" not in context

    assert target.getvalue().count("[justjobs]") == 2
