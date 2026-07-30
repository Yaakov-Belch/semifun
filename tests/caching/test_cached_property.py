"""`cached_property`: compute once on first access, sync or async.

Covers [[semifun-caching]] and [[cached-property:async]].  The async half is
where the behaviour cannot be read off the source: the task is created
*eagerly* on attribute access, and awaiting a chain that leads back to itself
raises instead of hanging.
"""

import asyncio
from dataclasses import dataclass

import pytest

from semifun.caching.cached_property import cached_property


# Deadlock detection depends on the *cached* awaitable being returned again:
# if caching were broken, each access would create a fresh task and the cycle
# would spin instead of raising.  The tests below are therefore time-bound with
# `pytest.mark.timeout`, so a detector that stops working fails the run quickly
# instead of stalling it.  `asyncio.wait_for` is not enough here — it cancels
# the waiting coroutine but not two tasks deadlocked on each other.
DEADLOCK_TIMEOUT = 5


async def _await(awaitable):
    """Await from inside a freshly created task, to exercise the parent chain."""
    return await awaitable


# --- Sync ---

def test_computes_once_and_caches():
    calls = []

    class Service:
        @cached_property
        def value(self):
            calls.append('called')
            return 42

    service = Service()
    assert service.value == 42
    assert service.value == 42
    assert calls == ['called']


def test_the_cached_value_lands_in_the_instance_dict():
    """Caching works by shadowing the descriptor, which is why it is cheap."""

    class Service:
        @cached_property
        def value(self):
            return 42

    service = Service()
    assert 'value' not in service.__dict__
    service.value
    assert service.__dict__['value'] == 42


def test_works_on_a_frozen_dataclass():
    """Frozen blocks __setattr__; the descriptor writes to __dict__ directly."""
    calls = []

    @dataclass(frozen=True)
    class Config:
        name: str

        @cached_property
        def derived(self):
            calls.append('called')
            return f'{self.name}!'

    config = Config(name='db')
    assert config.derived == 'db!'
    assert config.derived == 'db!'
    assert calls == ['called']


def test_class_access_returns_the_descriptor():
    class Service:
        @cached_property
        def value(self):
            return 42

    assert isinstance(Service.value, cached_property)


def test_the_docstring_is_carried_over():
    class Service:
        @cached_property
        def value(self):
            """What it holds."""
            return 42

    assert Service.value.__doc__ == 'What it holds.'


def test_instances_do_not_share_a_cache():
    class Service:
        @cached_property
        def value(self):
            return object()

    assert Service().value is not Service().value


# --- Async ---

async def test_async_property_is_awaited_and_cached():
    calls = []

    class Service:
        @cached_property
        async def value(self):
            calls.append('called')
            return 42

    service = Service()
    assert await service.value == 42
    assert await service.value == 42
    assert calls == ['called']


async def test_async_task_is_created_on_access_not_on_await():
    """[[cached-property:async]]: the task is created eagerly on first access."""
    started = []

    class Service:
        @cached_property
        async def value(self):
            started.append('running')
            return 42

    service = Service()
    holder = service.value           # attribute access only
    assert started == []             # scheduled, not yet run

    await asyncio.sleep(0)           # give the loop a turn
    assert started == ['running']    # it ran without anyone awaiting it
    assert await holder == 42


@pytest.mark.timeout(DEADLOCK_TIMEOUT)
async def test_a_self_referential_property_raises_instead_of_hanging():
    class Service:
        @cached_property
        async def value(self):
            return await self.value

    with pytest.raises(ValueError, match='Deadlock'):
        await Service().value


@pytest.mark.timeout(DEADLOCK_TIMEOUT)
async def test_a_cycle_between_two_properties_is_detected():
    """The parent chain, not just identity, is what catches the indirect case."""

    class Service:
        @cached_property
        async def a(self):
            return await self.b

        @cached_property
        async def b(self):
            return await self.a

    with pytest.raises(ValueError, match='Deadlock'):
        await Service().a


async def test_awaiting_the_same_property_from_two_tasks_is_not_a_deadlock():
    """The negative case: concurrent waiters are ordinary, and must not raise."""

    class Service:
        @cached_property
        async def value(self):
            await asyncio.sleep(0)
            return 42

    service = Service()
    holder = service.value
    both = await asyncio.gather(
        asyncio.create_task(_await(holder)),
        asyncio.create_task(_await(holder)),
    )
    assert both == [42, 42]


async def test_an_async_property_may_await_another_one():
    """A chain that does not loop back must resolve normally."""

    class Service:
        @cached_property
        async def inner(self):
            return 21

        @cached_property
        async def outer(self):
            return await self.inner * 2

    assert await Service().outer == 42
