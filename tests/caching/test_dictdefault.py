"""`dictdefault`: get-or-create for plain dicts, in four variants.

Covers [[dictdefault]].  The claim that carries the most weight is the async
one — that the computation runs exactly once even when a second caller arrives
while the first is still running — because it cannot be established by reading.
"""

import asyncio

import pytest

from yb_tools.caching.dictdefault import dictdefault


# --- Sync, no key passed ---

def test_computes_on_first_access_and_caches():
    cache = {}
    calls = []

    def make():
        calls.append('called')
        return 'value'

    assert dictdefault(cache, 'k', make) == 'value'
    assert dictdefault(cache, 'k', make) == 'value'
    assert calls == ['called']


def test_distinct_keys_are_computed_separately():
    cache = {}
    calls = []

    def make():
        calls.append('called')
        return len(calls)

    assert dictdefault(cache, 'a', make) == 1
    assert dictdefault(cache, 'b', make) == 2
    assert dictdefault(cache, 'a', make) == 1


def test_kwargs_are_forwarded_to_the_factory():
    cache = {}

    def make(suffix):
        return f'value-{suffix}'

    assert dictdefault(cache, 'k', make, suffix='a') == 'value-a'


def test_kwargs_are_used_only_on_the_computing_call():
    """Documented in [[dictdefault]]: later kwargs are ignored, not re-applied."""
    cache = {}

    def make(suffix):
        return f'value-{suffix}'

    first = dictdefault(cache, 'k', make, suffix='a')
    second = dictdefault(cache, 'k', make, suffix='b')
    assert first == 'value-a'
    assert second == 'value-a'


# --- Sync, key passed to the factory ---

def test_k_variant_passes_the_key():
    cache = {}

    def make(key):
        return f'made-{key}'

    assert dictdefault.k(cache, 'alice', make) == 'made-alice'


def test_k_variant_passes_the_key_alongside_kwargs():
    cache = {}

    def make(key, suffix):
        return f'{key}-{suffix}'

    assert dictdefault.k(cache, 'alice', make, suffix='x') == 'alice-x'


# --- Async ---

async def test_async_computes_once_and_caches():
    cache = {}
    calls = []

    async def make():
        calls.append('called')
        return 'value'

    assert await dictdefault.a(cache, 'k', make) == 'value'
    assert await dictdefault.a(cache, 'k', make) == 'value'
    assert calls == ['called']


async def test_async_runs_once_when_a_second_caller_arrives_mid_flight():
    """The central claim: a task is stored, so both callers await the same one."""
    calls = []
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow():
        calls.append('called')
        started.set()
        await release.wait()
        return 'value'

    cache = {}
    first = asyncio.create_task(dictdefault.a(cache, 'k', slow))
    await started.wait()                     # first is inside slow(), not finished

    second = asyncio.create_task(dictdefault.a(cache, 'k', slow))
    await asyncio.sleep(0)                   # let the second caller reach the cache

    release.set()
    assert await first == 'value'
    assert await second == 'value'
    assert calls == ['called']


async def test_ak_variant_passes_the_key():
    cache = {}

    async def make(key):
        return f'made-{key}'

    assert await dictdefault.ak(cache, 'alice', make) == 'made-alice'


async def test_async_kwargs_are_forwarded():
    cache = {}

    async def make(suffix):
        return f'value-{suffix}'

    assert await dictdefault.a(cache, 'k', make, suffix='a') == 'value-a'


def test_a_failed_sync_computation_is_not_cached():
    """The sync contrast: the assignment never happens, so a retry recomputes."""
    cache = {}
    calls = []

    def failing():
        calls.append('called')
        raise RuntimeError('nope')

    for _ in range(2):
        with pytest.raises(RuntimeError, match='nope'):
            dictdefault(cache, 'k', failing)
    assert calls == ['called', 'called']
    assert cache == {}


async def test_a_failed_async_computation_stays_cached():
    """A stored task keeps its exception: the failure is cached, not retried."""
    cache = {}
    calls = []

    async def failing():
        calls.append('called')
        raise RuntimeError('nope')

    with pytest.raises(RuntimeError, match='nope'):
        await dictdefault.a(cache, 'k', failing)
    with pytest.raises(RuntimeError, match='nope'):
        await dictdefault.a(cache, 'k', failing)
    assert calls == ['called']
