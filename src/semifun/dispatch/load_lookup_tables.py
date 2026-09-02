def load_lookup_tables(entry_points_group: str):
    ...

def _dotted_module_name(root_package_name: str, relative_path: str) -> str:
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
    fname: str

    @cached_property
    def fn(self): return getattr(self.module_loader.module, self.fname)

