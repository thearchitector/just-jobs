from enum import Enum


class JobType(Enum):
    """Indicates the performance characteristic of the job to run."""

    IO_BOUND = "io-bound"
    """
    IO-bound tasks typically spend a majority of their time waiting for external
    services to complete, such as when read / writing to disk or sending / receiving
    network packets. Since they do not hold the GIL during that downtime, IO-bound
    jobs run in a ThreadPoolExecutor.
    """

    CPU_BOUND = "cpu-bound"
    """
    CPU-bound tasks typically perform many contiguous operations (like complex
    calculations) rather than wait for external services. Because they operate 
    continuously and hold the GIL, CPU-bound jobs run in a ProcessPoolExecutor.
    """
