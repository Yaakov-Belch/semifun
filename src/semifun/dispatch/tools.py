from dataclasses import field
from inspect import signature


def signature_without_Inject(fn: callable):
    ...

def factory_field(fn): return field(init=False, repr=False, default_factory=fn)
