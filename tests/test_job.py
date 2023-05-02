import pytest
from arq.worker import create_worker

from just_jobs import JobType, job
from just_jobs.typing import Context


@job()
async def async_task(ctx: Context, val: str):
    return val


@job(job_type=JobType.IO_BOUND)
def io_task(ctx: Context, val: str):
    return val


@job(job_type=JobType.CPU_BOUND)
def cpu_task(ctx: Context, val: str):
    return val


@pytest.mark.parametrize("func", [async_task, cpu_task, io_task])
async def test_invoke_now(func):
    val = f"this is from {func.__name__}"
    res = await func.now(val)
    assert res == val


@pytest.mark.parametrize("func", [async_task, cpu_task, io_task])
async def test_enqueue_job(pool, settings, func, pcapture):
    val = f"this is from {func.__name__}"
    job = await pool.enqueue_job(func.__name__, val)

    worker = create_worker(
        settings_cls=settings,
        functions=[func],
        redis_pool=pool,
        burst=True,
        poll_delay=0,
    )
    with pcapture:
        await worker.main()
        await worker.close()

    res = await job.result(poll_delay=0)
    assert res == val
