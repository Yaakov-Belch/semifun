from dataclasses import field
from inspect import signature

from .Inject import injected_type


def signature_without_Inject(fn):
    """Return fn's signature with Inject[…] parameters removed."""
    sig = signature(fn)
    return sig.replace(parameters=[
        p for p in sig.parameters.values()
        if injected_type(p.annotation) is None
    ])

def factory_field(fn): return field(init=False, repr=False, default_factory=fn)
