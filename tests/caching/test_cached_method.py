"""`cached_method`: results keyed by a content hash of the call arguments.

Covers [[cached-method]].  The instance must supply a `cache_codec` with
`hash_to_bytes`; these tests bring their own, from `conftest.py`, because the
real one lives above this package in the dependency graph.
"""

import asyncio
from dataclasses import dataclass

import pytest

from yb_tools.caching.cached_method import cached_method


@dataclass(frozen=True)
class Repo:
    cache_codec: object
    calls: list

    @cached_method
    def fetch(self, item_id):
        self.calls.append(item_id)
        return f'item-{item_id}'

    @cached_method
    def other(self, item_id):
        self.calls.append(f'other:{item_id}')
        return f'other-{item_id}'

    @cached_method
    async def fetch_async(self, item_id):
        self.calls.append(f'async:{item_id}')
        await asyncio.sleep(0)
        return f'item-{item_id}'


@pytest.fixture
def repo(codec):
    return Repo(cache_codec=codec, calls=[])


# --- Sync ---

def test_repeated_calls_with_the_same_argument_hit_the_cache(repo):
    assert repo.fetch('a') == 'item-a'
    assert repo.fetch('a') == 'item-a'
    assert repo.calls == ['a']


def test_different_arguments_are_cached_separately(repo):
    repo.fetch('a')
    repo.fetch('b')
    repo.fetch('a')
    assert repo.calls == ['a', 'b']


def test_each_method_has_its_own_cache(repo):
    """Two methods called with the same argument must not collide."""
    assert repo.fetch('a') == 'item-a'
    assert repo.other('a') == 'other-a'
    assert repo.calls == ['a', 'other:a']


def test_instances_do_not_share_a_cache(codec):
    first = Repo(cache_codec=codec, calls=[])
    second = Repo(cache_codec=codec, calls=[])
    first.fetch('a')
    second.fetch('a')
    assert first.calls == ['a']
    assert second.calls == ['a']


def test_the_cache_is_installed_on_a_frozen_instance(repo):
    """`object.__setattr__` is what makes this work on a frozen dataclass."""
    repo.fetch('a')
    assert repo.__dict__['_method_cache_fetch']


def test_a_missing_cache_codec_fails_at_the_first_call():
    """[[cached-method]] requires the attribute; without it there is no key."""

    @dataclass(frozen=True)
    class NoCodec:
        @cached_method
        def fetch(self, item_id):
            return item_id

    with pytest.raises(AttributeError):
        NoCodec().fetch('a')


# --- Argument normalisation ---

@dataclass(frozen=True)
class Sized:
    cache_codec: object
    calls: list

    @cached_method
    # test-fixture-data: the default is the subject — the key is built from
    # bound arguments after `apply_defaults()`, so omitting it must not create
    # a second cache entry.
    def measure(self, name, size=10):   # test-fixture-data
        self.calls.append((name, size))
        return f'{name}:{size}'


def test_an_omitted_default_keys_the_same_as_passing_it_positionally(codec):
    sized = Sized(cache_codec=codec, calls=[])
    assert sized.measure('x') == 'x:10'
    assert sized.measure('x', 10) == 'x:10'
    assert sized.calls == [('x', 10)]


def test_keyword_and_positional_calls_share_one_cache_entry(codec):
    """The same call spelled three ways is cached once.

    `BoundArguments.args` places every POSITIONAL_OR_KEYWORD argument
    positionally, so `measure('x')`, `measure('x', 10)` and
    `measure('x', size=10)` all normalise to the key `('x', 10)`.
    """
    sized = Sized(cache_codec=codec, calls=[])
    assert sized.measure('x') == 'x:10'
    assert sized.measure('x', 10) == 'x:10'
    assert sized.measure('x', size=10) == 'x:10'
    assert sized.calls == [('x', 10)]


# --- Async ---

async def test_async_method_is_cached(repo):
    assert await repo.fetch_async('a') == 'item-a'
    assert await repo.fetch_async('a') == 'item-a'
    assert repo.calls == ['async:a']


async def test_async_method_runs_once_under_concurrent_callers(repo):
    """Async caching routes through `dictdefault.a`, which stores a task."""
    both = await asyncio.gather(
        repo.fetch_async('a'),
        repo.fetch_async('a'),
    )
    assert both == ['item-a', 'item-a']
    assert repo.calls == ['async:a']
