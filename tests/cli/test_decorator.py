"""Tests for the sync_function_owns_async_loop decorator."""

from semifun.cli.decorator import sync_function_owns_async_loop


def test_decorator_sets_attribute():
    @sync_function_owns_async_loop
    def serve():
        pass
    assert serve.sync_function_owns_async_loop is True


def test_decorator_preserves_function():
    def serve():
        return 42
    decorated = sync_function_owns_async_loop(serve)
    assert decorated is serve
    assert decorated() == 42


def test_undecorated_function_has_no_attribute():
    def serve():
        pass
    assert not getattr(serve, 'sync_function_owns_async_loop', False)
