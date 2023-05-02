import os
from hashlib import blake2b
from secrets import compare_digest
from typing import Any, Tuple

import dill  # type: ignore
from colorama import Fore, Style

from .broker import Broker
from .job_type import JobType
from .typing import Context
from .utils import styled_text

SERIALIZATION_SECRET: bytes = os.getenv(
    "JOB_SERIALIZATION_SECRET", "thisisasecret"
).encode("utf-8")


class BaseSettings(type):
    """
    A Metaclass for defining WorkerSettings to pass to an arq process. This enables
    using the built-in JobType and executor pool logic, as well as secure remote job
    serialization and parsing.
    """

    @staticmethod
    async def on_startup(ctx: Context) -> None:
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

    @staticmethod
    async def on_shutdown(ctx: Context) -> None:
        """
        Gracefully shuts down the available thread and process pool executors.
        """
        for executor in ctx["_executors"].values():
            executor.shutdown(wait=True)

        del ctx["_executors"]

        with styled_text(Fore.BLUE, Style.DIM):
            print("[justjobs] Gracefully shutdown executors ✔")

    @staticmethod
    def secure_serializer(job: Any) -> bytes:
        """
        Efficiently serializes the given job using dill and signs it using
        blake2b. During execution the signature is extracted and compare to the
        job function to ensure the intended job is run.
        """
        serialized: bytes = dill.dumps(job)
        signer = blake2b(key=SERIALIZATION_SECRET)
        signer.update(serialized)
        # must be hexdigest to ensure no premature byte delimiters
        sig = signer.hexdigest()
        return (sig + "|").encode("utf-8") + serialized

    @staticmethod
    def secure_deserializer(packed: bytes) -> Any:
        """
        Extracts the signature from the serialized job and compares it with the job
        function. If the signatures match, the job is deserialized and executed. If
        not, an error is raised.
        """
        sig, serialized = packed.split(b"|", 1)
        signer = blake2b(key=SERIALIZATION_SECRET)
        signer.update(serialized)

        if not compare_digest(sig.decode("utf-8"), signer.hexdigest()):
            raise ValueError(
                "Invalid job signature! Has someone tampered with your job queue?"
            )

        return dill.loads(serialized)

    def __new__(cls, clsname: str, bases: Tuple[Any, ...], attrs: Any) -> type:
        nattrs = dict(
            **attrs,
            on_startup=BaseSettings.on_startup,
            on_shutdown=BaseSettings.on_shutdown,
            job_serializer=BaseSettings.secure_serializer,
            job_deserializer=BaseSettings.secure_deserializer,
            create_pool=lambda **kwargs: Broker(
                redis_settings=attrs["redis_settings"],
                packj=BaseSettings.secure_serializer,
                unpackj=BaseSettings.secure_deserializer,
                kwargs=kwargs,
            ),
        )
        return super().__new__(cls, clsname, bases, nattrs)
