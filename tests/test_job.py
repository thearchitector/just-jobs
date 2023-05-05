import asyncio
from multiprocessing import current_process
from os import getpid
from threading import get_ident

import pytest

from just_jobs import Context, JobType, job


@job()
async def failing_task():
    raise Exception("mock error")


@job()
async def async_task(val: str, ctx: Context):
    return f"{getpid()}{val}{get_ident()}"


@job(job_type=JobType.IO_BOUND)
def io_task(ctx: Context, val: str):
    return f"{getpid()}{val}{get_ident()}"


@job(job_type=JobType.CPU_BOUND)
def cpu_task(val: str):
    return f"{current_process().pid}{val}{get_ident()}"


@job(job_type=JobType.CPU_BOUND)
def async_cpu_task(ctx: Context, val: str):
    async def f(val: str):
        return f"{getpid()}{val}{get_ident()}"

    task = f(val)
    return asyncio.run(task) if ctx else task


@pytest.mark.parametrize("func", [async_task, cpu_task, io_task, async_cpu_task])
async def test_invoke_now(func):
    res = await func.now(" on ")
    assert res == f"{getpid()} on {get_ident()}"


async def test_failing_now():
    with pytest.raises(Exception, match="mock"):
        await failing_task.now()


async def test_enqueue_job_async(enqueue_run_job):
    # test async is on same process and thread
    job = await enqueue_run_job(async_task, " on ")
    res = await job.result(poll_delay=0)
    assert res == f"{getpid()} on {get_ident()}"


async def test_enqueue_job_io(enqueue_run_job):
    # test io is on same process but different thread
    job = await enqueue_run_job(io_task, " on ")
    res = await job.result(poll_delay=0)
    process, thread = res.split(" on ")
    assert process == str(getpid())
    assert thread != str(get_ident())


@pytest.mark.parametrize("func", [cpu_task, async_cpu_task])
async def test_enqueue_job_cpu(func, enqueue_run_job):
    # test cpu is on different process
    job = await enqueue_run_job(func, " on ")
    res = await job.result(poll_delay=0)
    process, thread = res.split(" on ")
    assert process != str(getpid())
    # assert thread != str(get_ident())


async def test_enqueue_job_fail(enqueue_run_job):
    job = await enqueue_run_job(failing_task)

    with pytest.raises(Exception, match="mock"):
        await job.result(poll_delay=0)
