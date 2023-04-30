import concurrent.futures as cf
import os
from enum import Enum


class JobType(Enum):
    """
    Indicates the performance characteristic of the job to run.

    IO-bound tasks typically spend a majority of their time waiting for external
    services to complete, such as when read / writing to disk or sending / receiving
    network requests. Since they do not hold the GIL during that downtime, IO-bound
    jobs will run in a ThreadPoolExecutor.

    CPU-bound tasks typically perform many operations (like complex calculations)
    rather than wait for external services. Because they operate continuously and hold
    the GIL, CPU-bound jobs will run in a ProcessPoolExecutor.
    """

    IO_BOUND = (cf.ThreadPoolExecutor, os.getenv("MAX_THREAD_WORKERS"))
    CPU_BOUND = (cf.ProcessPoolExecutor, os.getenv("MAX_PROCESS_WORKERS"))
