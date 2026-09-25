from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from backend.distro import DistroInfo
from backend.prereq import PrereqSpec, PrereqType

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


class CatalogError(Exception):
    pass


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    description: str
    package_manager_override: str | None
    search_terms: dict[str, str]
    prereqs: list[PrereqSpec]


@dataclass(frozen=True)
class ResolvedTarget:
    entry: CatalogEntry
    package_manager: str
    term: str


def _parse_prereq(raw: dict, index: int, entry_name: str) -> PrereqSpec:
    try:
        prereq_type = PrereqType(raw["type"])
    except (KeyError, ValueError) as exc:
        raise CatalogError(
            f"{entry_name}: invalid prereq type at index {index}: {raw.get('type')!r}"
        ) from exc
    return PrereqSpec(type=prereq_type, repo=raw.get("repo"))


def _parse_entry(raw: dict, index: int) -> CatalogEntry:
    try:
        name = raw["name"]
    except KeyError as exc:
        raise CatalogError(f"Catalog entry at index {index} is missing 'name'") from exc

    search_terms = raw.get("search_terms") or {}
    if not search_terms:
        raise CatalogError(f"{name}: 'search_terms' must not be empty")

    prereqs_raw = raw.get("prereqs") or []
    prereqs = [_parse_prereq(p, i, name) for i, p in enumerate(prereqs_raw)]

    return CatalogEntry(
        name=name,
        description=raw.get("description", ""),
        package_manager_override=raw.get("package_manager_override"),
        search_terms=search_terms,
        prereqs=prereqs,
    )


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> list[CatalogEntry]:
    try:
        raw_text = Path(path).read_text()
    except OSError as exc:
        raise CatalogError(f"Could not read catalog file at {path}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Catalog file at {path} is not valid JSON: {exc}") from exc

    programs = data.get("programs")
    if not isinstance(programs, list):
        raise CatalogError(f"Catalog file at {path} must have a top-level 'programs' list")

    return [_parse_entry(raw, i) for i, raw in enumerate(programs)]


def resolve_target(entry: CatalogEntry, distro: DistroInfo) -> ResolvedTarget | None:
    pm = entry.package_manager_override or distro.package_manager
    if not pm:
        return None
    term = entry.search_terms.get(pm)
    if term is None:
        return None
    return ResolvedTarget(entry=entry, package_manager=pm, term=term)
