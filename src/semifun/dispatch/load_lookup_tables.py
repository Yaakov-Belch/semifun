import importlib
import importlib.metadata
import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path

from semifun.caching.cached_property import cached_property


ANNOTATION_RE = re.compile(r'^#::(\w+):(.+)$')


def load_lookup_tables(*, entry_points_group: str) -> dict[str, dict[str, 'FnLoader']]:
    """Discover packages via entry points, scan for #:: annotations, return lookup tables.

    Returns {ftype: {fname: FnLoader}}.

    Each `#::ftype:fname` comment in a .py file registers the function `fname`
    from that module under (ftype, fname).  `#::ftype:fname=alias` registers the
    Python attribute `alias` under the lookup key `fname`.
    """
    tables: dict[str, dict[str, FnLoader]] = {}
    for ep in importlib.metadata.entry_points(group=entry_points_group):
        package_name = ep.value
        package_path = _find_package_path(package_name)
        _scan_package_into(tables, package_name=package_name, package_path=package_path)
    return tables


def _find_package_path(package_name: str) -> Path:
    spec = importlib.util.find_spec(package_name)
    if spec is None or spec.submodule_search_locations is None:
        raise ImportError(f"Package not found: {package_name}")
    return Path(spec.submodule_search_locations[0])


def _scan_package_into(
    tables: dict[str, dict[str, 'FnLoader']],
    *,
    package_name: str,
    package_path: Path,
) -> None:
    for py_file in sorted(package_path.rglob('*.py')):
        rel = str(py_file.relative_to(package_path))
        dotted = _dotted_module_name(root_package_name=package_name, relative_path=rel)
        module_loader = ModuleLoader(dotted_module_name=dotted)
        for line in py_file.read_text().splitlines():
            m = ANNOTATION_RE.match(line.strip())
            if m is None:
                continue
            ftype = m.group(1)
            value = m.group(2)
            if '=' in value:
                fname, alias = value.split('=', 1)
            else:
                fname = value
                alias = value
            ftype_table = tables.setdefault(ftype, {})
            if fname in ftype_table:
                existing = ftype_table[fname]
                raise LookupError(
                    f"Duplicate #::{ftype}:{fname} — "
                    f"{existing.module_loader.dotted_module_name}.{existing.fname_alias} "
                    f"and {dotted}.{alias}"
                )
            ftype_table[fname] = FnLoader(module_loader=module_loader, fname_alias=alias)


def _dotted_module_name(*, root_package_name: str, relative_path: str) -> str:
    """Compose the dotted module name for a file inside an installed package.

    Examples:
        ('foo', 'bar/foobar.py')   -> foo.bar.foobar
        ('foo', 'bar/__init__.py') -> foo.bar
        ('foo', '__init__.py')     -> foo
    """

    parts = list(Path(relative_path).with_suffix('').parts)
    if parts and parts[-1] == '__init__':
        parts.pop()
    return '.'.join([root_package_name, *parts])


@dataclass(frozen=True)
class ModuleLoader:
    dotted_module_name: str

    @cached_property
    def module(self): return importlib.import_module(self.dotted_module_name)

@dataclass(frozen=True)
class FnLoader:
    module_loader: ModuleLoader
    fname_alias: str

    @cached_property
    def fn(self): return getattr(self.module_loader.module, self.fname_alias)

@dataclass(frozen=True)
class LoadedFn:
    """Pre-loaded function wrapper, matching the .fn interface of FnLoader.

    In production, SemifunApp receives an entry_points_group string and
    load_lookup_tables builds {ftype: {fname: FnLoader}} with lazy loading.
    For testing, pass a dict directly as entry_points_group, wrapping each
    callable in LoadedFn so lookup_fn/fn_items can access .fn uniformly:

        test_app = SemifunApp(entry_points_group={
            'cli': {'hello': LoadedFn(fn=hello), ...},
        })
    """
    fn: callable

