import os
from hashlib import blake2b
from secrets import compare_digest

import dill
from arq import create_pool
from arq.connections import RedisSettings
from colorama import Fore, Style

from .job_type import JobType
from .typing import Context
from .utils import styled_text

SERIALIZATION_SECRET = os.getenv("JOB_SERIALIZATION_SECRET", "thisisasecret").encode(
    "utf-8"
)


class BaseSettings(type):
    """
    A Metaclass for defining WorkerSettings to pass to an arq process. This enables
    using the built-in JobType and executor pool logic, as well as secure remote job
    serialization and parsing.
    """

    async def on_startup(ctx: Context):
        """
        Starts the thread and process pool executors for downstream synchronous job
        execution.
        """
        with styled_text(Fore.BLUE, Style.DIM):
            print("[justjobs] Starting executors...")

        # we're ok creating pools for all the types since the executors don't
        # spin up the threads / processes unless a task is scheduled to run in one
        ctx["_executors"] = {
            jtype: jtype.value[0](max_workers=jtype.value[1]) for jtype in JobType
        }

    async def on_shutdown(ctx: Context):
        """
        Gracefully shuts down the available thread and process pool executors.
        """
        for executor in ctx["_executors"].values():
            executor.shutdown(wait=True)

        with styled_text(Fore.BLUE, Style.DIM):
            print("[justjobs] Gracefully shutdown executors ✔")

    def secure_serializer(job):
        """
        Efficiently serializes the given job using dill and signs it using
        blake2b. During execution the signature is extracted and compare to the
        job function to ensure the intended job is run.
        """
        serialized = dill.dumps(job)
        signer = blake2b(key=SERIALIZATION_SECRET)
        signer.update(serialized)
        # must be hexdigest to ensure no premature byte delimiters
        sig = signer.hexdigest()
        return (sig + "|").encode("utf-8") + serialized

    def secure_deserializer(packed):
        """
        Extracts the signature from the serialized job and compares it with the job
        function. If the signatures match, the job is deserialized and executed. If
        not, an error is raised.
        """
        sig, serialized = packed.split(b"|", 1)
        signer = blake2b(key=SERIALIZATION_SECRET)
        signer.update(serialized)
        assert compare_digest(
            sig.decode("utf-8"), signer.hexdigest()
        ), "Invalid job signature! Has someone tampered with your job queue?"

        return dill.loads(serialized)

    def create_broker(redis_settings: RedisSettings):
        """
        Creates a ArqRedis client via `create_pool` using the class's defined
        `redis_settings` and secure serialization logic.
        """

        async def wrapper(**kwargs):
            nonlocal redis_settings
            return await create_pool(
                redis_settings,
                job_serializer=BaseSettings.secure_serializer,
                job_deserializer=BaseSettings.secure_deserializer,
                **kwargs,
            )

        return wrapper

    def __new__(cls, clsname, bases, attrs):
        nattrs = dict(
            **attrs,
            on_startup=BaseSettings.on_startup,
            on_shutdown=BaseSettings.on_shutdown,
            job_serializer=BaseSettings.secure_serializer,
            job_deserializer=BaseSettings.secure_deserializer,
            create_broker=BaseSettings.create_broker(attrs["redis_settings"]),
        )
        return super().__new__(cls, clsname, bases, nattrs)
