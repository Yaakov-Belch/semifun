"""Tests for the di_plugin_feature wrapper."""

import pytest
from unittest.mock import AsyncMock

from semifun.di.di_plugin_feature import di_plugin_feature


async def test_di_plugin_feature_calls_through(monkeypatch):
    """The wrapper looks up the feature, gets the injector, seeds it, and calls."""
    call_log = {}

    async def fake_fn(x, y):
        call_log['args'] = (x, y)
        return x + y

    class FakeFeatureMap:
        def __call__(self, *, feature):
            call_log['feature'] = feature
            return fake_fn

    class FakeDI:
        def with_seed_data(self, seed_data):
            call_log['seed_data'] = seed_data
            return self

        async def async_call_with_args(self, *, fn, args, kwargs):
            return await fn(*args, **kwargs)

    class FakeSeed:
        pass

    monkeypatch.setattr(
        'semifun.di.di_plugin_feature.get_cached_feature_map',
        lambda plugin_type: FakeFeatureMap() if plugin_type == 'my_plugin' else None,
    )
    monkeypatch.setattr(
        'semifun.di.di_plugin_feature.get_injector',
        lambda injector_type: FakeDI() if injector_type == 'my_injector' else None,
    )

    result = await di_plugin_feature(
        plugin_type='my_plugin',
        feature='do_thing',
        args=(3, 4),
        kwargs={},
        injector_type='my_injector',
        seed_data={FakeSeed: FakeSeed()},
    )

    assert call_log['feature'] == 'do_thing'
    assert call_log['args'] == (3, 4)
    assert FakeSeed in call_log['seed_data']
