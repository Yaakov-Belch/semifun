"""Shared fixtures.

`conftest.py` is where test code shared between modules lives: under
`--import-mode=importlib` (see [[:workspace-test-setup]]) the `tests/`
directory is not on `sys.path`, so a sibling helper module cannot be imported.
"""

from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class FakeCodec:
    """Stands in for the content-hashing codec `cached_method` requires.

    In production that is a `TmsgpackCodec`, but `tmsgpack` sits *above*
    `semifun-caching` in the dependency graph of
    [[:in-tree-infrastructure-libraries]], and [[:independent-packages]]
    forbids depending upward — in tests as much as in source.  Hashing by
    `repr` is deterministic within a run, which is all a cache key needs.
    """

    def hash_to_bytes(self, value) -> bytes:
        return repr(value).encode()


@pytest.fixture
def codec():
    return FakeCodec()
