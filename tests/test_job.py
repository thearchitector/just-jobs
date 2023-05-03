from multiprocessing import current_process
from os import getpid
from threading import get_ident

import pytest

from just_jobs import JobType, job
from just_jobs.typing import Context


@job()
async def async_task(ctx: Context, val: str):
    return f"{getpid()}{val}{get_ident()}"


@job(job_type=JobType.IO_BOUND)
def io_task(ctx: Context, val: str):
    return f"{getpid()}{val}{get_ident()}"


@job(job_type=JobType.CPU_BOUND)
def cpu_task(ctx: Context, val: str):
    return f"{current_process().pid}{val}{get_ident()}"


@pytest.mark.parametrize("func", [async_task, cpu_task, io_task])
async def test_invoke_now(func):
    res = await func.now(" on ")
    assert res == f"{getpid()} on {get_ident()}"


async def test_enqueue_job_async(enqueue_run_job):
    # test async is on same process and thread
    res = await enqueue_run_job(async_task, " on ")
    assert res == f"{getpid()} on {get_ident()}"


async def test_enqueue_job_io(enqueue_run_job):
    # test io is on same process but different thread
    res = await enqueue_run_job(io_task, " on ")
    process, thread = res.split(" on ")
    assert process == str(getpid())
    assert thread != str(get_ident())


async def test_enqueue_job_cpu(enqueue_run_job):
    # test cpu is on different process
    res = await enqueue_run_job(cpu_task, " on ")
    process, thread = res.split(" on ")
    assert process != str(getpid())
