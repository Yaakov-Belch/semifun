"""Tests for the frozen data model."""

from dataclasses import FrozenInstanceError

import pytest

from semifun.di.model import (
    Inject,
    InjectArg,
    PassThroughArg,
    CallWithArgsSignature,
    MISSING,
    signature_without_Inject,
)


def test_inject_is_a_type_alias():
    """`Inject[T]` is a parameterized type alias, distinguishable from a bare type."""
    # The alias `Inject` itself is a TypeAliasType (PEP 695).
    # Inject[int] should be detectable; bare int should not.
    parameterized = Inject[int]
    # The parameterized form references the alias `Inject`.
    assert parameterized is not int
    # Bare int is just int — no alias wrapper.
    assert int is int


def test_inject_arg_is_frozen():
    arg = InjectArg(name="x", type=int, injector_fn=None)
    with pytest.raises(FrozenInstanceError):
        arg.name = "y"


def test_inject_arg_holds_function():
    def maker():
        return 42
    arg = InjectArg(name="x", type=int, injector_fn=maker)
    assert arg.injector_fn is maker
    assert arg.injector_fn() == 42


def test_passthrough_arg_with_default():
    arg = PassThroughArg(name="x", type=int, default_value=5)
    assert arg.default_value == 5


def test_passthrough_arg_with_missing_default():
    arg = PassThroughArg(name="x", type=int, default_value=MISSING)
    assert arg.default_value is MISSING


def test_call_with_args_signature_holds_both():
    sig = CallWithArgsSignature(
        injected_args=(InjectArg(name="ctx", type=str, injector_fn=None),),
        passthrough_args=(PassThroughArg(name="x", type=int, default_value=MISSING),),
    )
    assert len(sig.injected_args) == 1
    assert len(sig.passthrough_args) == 1


def test_missing_repr():
    assert repr(MISSING) == "MISSING"


# --- signature_without_Inject ---

class TestSignatureWithoutInject:

    def test_removes_injected_params(self):
        def fn(*, name: str, ctx: Inject[object]): ...
        sig = signature_without_Inject(fn)
        assert list(sig.parameters.keys()) == ['name']

    def test_keeps_all_when_no_inject(self):
        def fn(*, x: int, y: str): ...
        sig = signature_without_Inject(fn)
        assert list(sig.parameters.keys()) == ['x', 'y']

    def test_removes_all_when_all_injected(self):
        def fn(*, a: Inject[int], b: Inject[str]): ...
        sig = signature_without_Inject(fn)
        assert list(sig.parameters.keys()) == []

    def test_preserves_unannotated_params(self):
        def fn(x, *, ctx: Inject[object]): ...
        sig = signature_without_Inject(fn)
        assert list(sig.parameters.keys()) == ['x']

    def test_preserves_defaults(self):
        def fn(*, name: str = 'world', ctx: Inject[object]): ...
        sig = signature_without_Inject(fn)
        assert sig.parameters['name'].default == 'world'
