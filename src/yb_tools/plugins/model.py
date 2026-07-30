import importlib
from dataclasses import dataclass
from pathlib import Path

from yb_tools.caching.cached_property import cached_property


# --- All-knowable-data frozen dataclasses ---

@dataclass(frozen=True)
class FeatureSpec:
    """Parsed from a #::<feature_type>:<name> or #::<feature_type>:<name>=<alias> line."""
    feature_type: str
    feature_name: str
    feature_alias: str | None


@dataclass(frozen=True)
class IndexedFile:
    """One source file: where it lives, and what it declares."""
    file_path: Path
    feature_package: str
    dotted_module_name: str
    entry_point_group: str | None
    entry_point_name: str | None
    feature_specs: tuple[FeatureSpec, ...]


@dataclass(frozen=True)
class FeatureMatch:
    """One match: a feature declaration paired with the file it was found in."""
    indexed_file: IndexedFile
    feature_spec: FeatureSpec

    @cached_property
    def loaded_object(self):
        """Import the module and return the named Python object."""
        module = importlib.import_module(self.indexed_file.dotted_module_name)
        name = self.feature_spec.feature_alias or self.feature_spec.feature_name
        return getattr(module, name)


@dataclass(frozen=True)
class FeatureMatches:
    """Query result: zero or more feature matches."""
    matches: tuple[FeatureMatch, ...]

    @cached_property
    def single(self) -> FeatureMatch:
        """The unique match. Raises if zero or ambiguous (after specificity)."""
        if len(self.matches) == 0:
            raise LookupError("No matching feature found")
        if len(self.matches) == 1:
            return self.matches[0]
        # Specificity: explicit alias wins over implicit
        explicit = [m for m in self.matches if m.feature_spec.feature_alias is not None]
        implicit = [m for m in self.matches if m.feature_spec.feature_alias is None]
        if len(explicit) == 1:
            return explicit[0]
        if len(explicit) > 1:
            names = [f'{m.indexed_file.feature_package}:{m.feature_spec.feature_name}='
                     f'{m.feature_spec.feature_alias}' for m in explicit]
            raise LookupError(f"Ambiguous: multiple explicit overrides: {names}")
        names = [f'{m.indexed_file.feature_package}:{m.feature_spec.feature_name}'
                 for m in self.matches]
        raise LookupError(f"Ambiguous: multiple matches, no specificity resolution: {names}")

    @cached_property
    def loaded_object(self):
        """Convenience: the single match's loaded object."""
        return self.single.loaded_object

    @cached_property
    def by_name(self) -> dict[str, FeatureMatch]:
        """Index matches by feature_name, applying specificity on clash."""
        result: dict[str, FeatureMatch] = {}
        for m in self.matches:
            key = m.feature_spec.feature_name
            if key not in result:
                result[key] = m
                continue
            existing = result[key]
            has_alias = m.feature_spec.feature_alias is not None
            existing_has_alias = existing.feature_spec.feature_alias is not None
            if has_alias and not existing_has_alias:
                result[key] = m
            elif existing_has_alias and not has_alias:
                pass
            else:
                raise LookupError(
                    f"Ambiguous: '{key}' from '{m.indexed_file.feature_package}' "
                    f"and '{existing.indexed_file.feature_package}'"
                )
        return result


@dataclass(frozen=True)
class FeaturePluginsIndex:
    """The combined index of all features. Main query interface."""
    indexed_files: tuple[IndexedFile, ...]

    @cached_property
    def _all_matches(self) -> tuple[FeatureMatch, ...]:
        """Every declaration in every indexed file."""
        return tuple(
            FeatureMatch(indexed_file=f, feature_spec=fs)
            for f in self.indexed_files
            for fs in f.feature_specs
        )

    def find_features(
        self,
        feature_type: str | None,
        feature_name: str | None,
        feature_package: str | None,
    ) -> FeatureMatches:
        """Find features matching the given criteria. None = match any.

        All three filters are required: `None` is a meaningful value ("match
        any") and must be passed explicitly.
        """
        matches = self._all_matches
        if feature_type is not None:
            matches = tuple(m for m in matches if m.feature_spec.feature_type == feature_type)
        if feature_name is not None:
            matches = tuple(m for m in matches if m.feature_spec.feature_name == feature_name)
        if feature_package is not None:
            matches = tuple(m for m in matches if m.indexed_file.feature_package == feature_package)
        return FeatureMatches(matches=matches)

    @cached_property
    def verify_no_clashes(self) -> bool:
        """Check that no (feature_type, feature_name, feature_package) triple is ambiguous.
        Raises LookupError on first clash found. Returns True if clean."""
        seen: dict[tuple[str, str, str], FeatureMatch] = {}
        for m in self._all_matches:
            key = (m.feature_spec.feature_type, m.feature_spec.feature_name,
                   m.indexed_file.feature_package)
            if key not in seen:
                seen[key] = m
                continue
            existing = seen[key]
            has_alias = m.feature_spec.feature_alias is not None
            existing_has_alias = existing.feature_spec.feature_alias is not None
            if has_alias != existing_has_alias:
                if has_alias:
                    seen[key] = m
            else:
                raise LookupError(
                    f"Clash: {key} declared in both "
                    f"'{m.indexed_file.file_path}' and '{existing.indexed_file.file_path}'"
                )
        return True
