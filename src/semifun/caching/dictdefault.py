"""dictdefault — a caching accessor for normal dicts.

The name is a play on ``defaultdict``: instead of using a special dict type,
you use a normal dict and a caching accessor function.

Variants:

- ``dictdefault``    — sync, key not passed to the function.
- ``dictdefault.k``  — sync, key passed as first argument.
- ``dictdefault.a``  — async, key not passed.
- ``dictdefault.ak`` — async, key passed as first argument.

The async variants ensure the computation runs only once, even when
additional requests arrive while the first computation is still running.
All callers receive the same awaitable task object.

All variants accept ``**kwargs`` which are forwarded to the function.
They are considered only the first time — when the computation is performed.

``dictdefault.async_cache(d)`` wraps each value in ``d`` as a resolved
``asyncio.Future``, returning a cache dict that ``dictdefault.a`` can use
with pre-populated (seed) values alongside computed entries.

Example::

    cache1 = {}; cache2 = {}  # sync and async use distinct caching formats
    config  = dictdefault(cache1, 'db', load_config)        # → load_config()
    user    = dictdefault.k(cache1, 'alice', fetch_user)    # → fetch_user('alice')
    session = await dictdefault.a(cache2, 'main', async_create_session)
        # → await async_create_session()
    page    = await dictdefault.ak(cache2, url, async_fetch_page)
        # → await async_fetch_page(url)

    # Pre-populate an async cache with plain values:
    cache3 = dictdefault.async_cache({'key': value})
    result = await dictdefault.a(cache3, 'key', compute_fn)  # → value (no compute)
"""

import asyncio


def _resolved_future(value):
    fut = asyncio.Future()
    fut.set_result(value)
    return fut


def _mk_dictdefault():
    def _dd(with_key):
        def dictdefault(_d, _key, _fn, **kwargs):
            if _key not in _d:
                _d[_key] = _fn(_key, **kwargs) if with_key else _fn(**kwargs)
            return _d[_key]
        return dictdefault

    def _dda(with_key):
        from semifun.caching.cached_property import create_task_loop_check
        async def dictdefault(_d, _key, _fn, **kwargs):
            if _key not in _d:
                _d[_key] = (
                  create_task_loop_check(
                      _fn(_key, **kwargs) if with_key else _fn(**kwargs),
                      name=None, context=None,
                  )
                )
            return await _d[_key]
        return dictdefault

    def _async_cache(d):
        return {k: _resolved_future(v) for k, v in d.items()}

    dictdefault    = _dd(False)
    dictdefault.k  = _dd(True)
    dictdefault.a  = _dda(False)
    dictdefault.ak = _dda(True)
    dictdefault.async_cache = _async_cache

    return dictdefault

dictdefault = _mk_dictdefault()
