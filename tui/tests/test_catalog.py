import json

import pytest

from backend.catalog import CatalogEntry, CatalogError, load_catalog, resolve_target
from backend.distro import DistroInfo
from backend.prereq import PrereqType


def _write_catalog(tmp_path, data):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data))
    return path


def test_load_catalog_basic(tmp_path):
    path = _write_catalog(
        tmp_path,
        {
            "programs": [
                {
                    "name": "Firefox",
                    "description": "Browser",
                    "package_manager_override": None,
                    "search_terms": {"dnf": "firefox"},
                    "prereqs": [],
                }
            ]
        },
    )
    entries = load_catalog(path)
    assert len(entries) == 1
    assert entries[0].name == "Firefox"


def test_load_catalog_with_prereq(tmp_path):
    path = _write_catalog(
        tmp_path,
        {
            "programs": [
                {
                    "name": "Topgrade",
                    "search_terms": {"dnf": "topgrade"},
                    "prereqs": [{"type": "copr", "repo": "lilay/topgrade"}],
                }
            ]
        },
    )
    entries = load_catalog(path)
    assert entries[0].prereqs[0].type == PrereqType.COPR
    assert entries[0].prereqs[0].repo == "lilay/topgrade"


def test_load_catalog_missing_name(tmp_path):
    path = _write_catalog(tmp_path, {"programs": [{"search_terms": {"dnf": "x"}}]})
    with pytest.raises(CatalogError):
        load_catalog(path)


def test_load_catalog_empty_search_terms(tmp_path):
    path = _write_catalog(tmp_path, {"programs": [{"name": "X", "search_terms": {}}]})
    with pytest.raises(CatalogError):
        load_catalog(path)


def test_load_catalog_invalid_prereq_type(tmp_path):
    path = _write_catalog(
        tmp_path,
        {"programs": [{"name": "X", "search_terms": {"dnf": "x"}, "prereqs": [{"type": "bogus"}]}]},
    )
    with pytest.raises(CatalogError):
        load_catalog(path)


def test_load_catalog_bad_json(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text("{not valid json")
    with pytest.raises(CatalogError):
        load_catalog(path)


def test_resolve_target_uses_native_pm():
    entry = CatalogEntry(
        name="Firefox",
        description="",
        package_manager_override=None,
        search_terms={"dnf": "firefox"},
        prereqs=[],
    )
    distro = DistroInfo(distro_name="Fedora", package_manager="dnf", package_manager_path="/usr/bin/dnf")
    target = resolve_target(entry, distro)
    assert target is not None
    assert target.package_manager == "dnf"
    assert target.term == "firefox"


def test_resolve_target_uses_override():
    entry = CatalogEntry(
        name="Discord",
        description="",
        package_manager_override="snap",
        search_terms={"snap": "discord"},
        prereqs=[],
    )
    distro = DistroInfo(distro_name="Fedora", package_manager="dnf", package_manager_path="/usr/bin/dnf")
    target = resolve_target(entry, distro)
    assert target is not None
    assert target.package_manager == "snap"
    assert target.term == "discord"


def test_resolve_target_missing_for_distro():
    entry = CatalogEntry(
        name="Firefox",
        description="",
        package_manager_override=None,
        search_terms={"apt": "firefox"},
        prereqs=[],
    )
    distro = DistroInfo(distro_name="Fedora", package_manager="dnf", package_manager_path="/usr/bin/dnf")
    assert resolve_target(entry, distro) is None
