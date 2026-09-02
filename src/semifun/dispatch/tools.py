from dataclasses import field


def factory_field(fn): return field(init=False, repr=False, default_factory=fn)
