"""Tests for converge.runtime.scheduler."""

import asyncio
import time

import pytest

from converge.runtime.scheduler import Scheduler


@pytest.mark.asyncio
async def test_scheduler_wake():
    scheduler = Scheduler()

    start = time.time()

    async def notifier():
        await asyncio.sleep(0.1)
        scheduler.notify()

    asyncio.create_task(notifier())

    woke = await scheduler.wait_for_work(timeout=1.0)
    duration = time.time() - start

    assert woke
    assert 0.1 <= duration < 0.2


@pytest.mark.asyncio
async def test_scheduler_timeout():
    scheduler = Scheduler()
    start = time.time()

    woke = await scheduler.wait_for_work(timeout=0.1)
    duration = time.time() - start

    assert not woke
    assert duration >= 0.1
