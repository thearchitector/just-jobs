import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from hashlib import blake2b
from secrets import compare_digest
from typing import Any, Dict, Tuple

import dill  # type: ignore
from colorama import Fore, Style

from .broker import Broker
from .job_type import JobType
from .typing import Context
from .utils import styled_text

SERIALIZATION_SECRET: bytes = os.getenv(
    "JOB_SERIALIZATION_SECRET", "thisisasecret"
).encode("utf-8")

MAX_THREAD_WORKERS = int(os.getenv("MAX_THREAD_WORKERS", 0)) or None
MAX_PROCESS_WORKERS = int(os.getenv("MAX_PROCESS_WORKERS", 0)) or None


class BaseSettings(type):
    """
    A metaclass for defining WorkerSettings to pass to an arq process. This enables
    using the built-in JobType and executor pool logic, as well as secure remote job
    serialization and parsing.
    """

    def __new__(
        cls, clsname: str, bases: Tuple[Any, ...], attrs: Dict[str, Any]
    ) -> type:
        attrs.update(
            {
                "on_startup": BaseSettings.on_startup,
                "on_shutdown": BaseSettings.on_shutdown,
                "job_serializer": BaseSettings.job_serializer,
                "job_deserializer": BaseSettings.job_deserializer,
            }
        )
        return super().__new__(cls, clsname, bases, attrs)

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
            JobType.IO_BOUND: ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS),
            JobType.CPU_BOUND: ProcessPoolExecutor(max_workers=MAX_PROCESS_WORKERS),
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
    def job_serializer(job: Any) -> bytes:
        """
        Serializes the given job using dill and signs it using blake2b. The serialized
        job and its signature are returned for later verification.
        """
        serialized: bytes = dill.dumps(job)
        signer = blake2b(key=SERIALIZATION_SECRET)
        signer.update(serialized)
        # must be hexdigest to ensure no premature byte delimiters
        sig = signer.hexdigest()
        return (sig + "|").encode("utf-8") + serialized

    @staticmethod
    def job_deserializer(packed: bytes) -> Any:
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

    def create_pool(cls, **kwargs: Any) -> Broker:
        """
        Creates an ArqRedis instance using this class' RedisSettings and job
        serializers. This function technically returns an instance of Broker,
        so the pool creation is delayed until the returned object is either
        awaited or entered.
        """
        if not hasattr(cls, "redis_settings"):
            raise AttributeError(
                "You must first define some RedisSettings on this worker class before"
                " trying to create a pool from them."
            )

        return Broker(
            redis_settings=cls.redis_settings,
            packj=cls.job_serializer,
            unpackj=cls.job_deserializer,
            kwargs=kwargs,
        )
