import pytest

from backend.distro import DistroInfo
from backend.logging_setup import SessionLogger
from ui.app import KNLBApp


@pytest.mark.asyncio
async def test_app_boots_and_shows_banner(tmp_path):
    distro = DistroInfo(distro_name="Fedora", package_manager="dnf", package_manager_path="/usr/bin/dnf")
    logger = SessionLogger(log_dir=tmp_path)
    app = KNLBApp(logger=logger, distro=distro)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#banner") is not None
        assert app.query_one("#program-list") is not None


@pytest.mark.asyncio
async def test_install_selected_shows_progress_and_blocks_rerun(tmp_path, monkeypatch):
    import asyncio

    from textual.widgets import Button

    from backend.catalog import CatalogEntry
    from backend.models import InstallOutcome
    from ui.widgets.program_catalog import ProgramCatalog

    distro = DistroInfo(distro_name="Fedora", package_manager="dnf", package_manager_path="/usr/bin/dnf")
    app = KNLBApp(logger=SessionLogger(log_dir=tmp_path), distro=distro)

    release = asyncio.Event()
    calls: list[str] = []

    async def fake_install(entry):
        calls.append(entry.name)
        await release.wait()
        return InstallOutcome(name=entry.name, ok=True, message="Installed")

    monkeypatch.setattr(app, "_install_catalog_entry", fake_install)
    monkeypatch.setattr(app, "_check_installed_async", lambda entries: None)
    monkeypatch.setattr(app, "_load_uninstall_list_async", lambda: None)

    async with app.run_test() as pilot:
        entry = CatalogEntry(
            name="nut", description="d", package_manager_override=None, search_terms={"dnf": "nut"}, prereqs=[]
        )
        app.query_one(ProgramCatalog).add_search_result(entry, select=True)
        button = app.query_one("#install-selected", Button)
        assert not button.disabled

        app._start_install_selected()
        await pilot.pause()
        assert button.disabled
        assert app.query_one("#status-progress").display

        app._start_install_selected()  # second run while busy is refused
        await pilot.pause()
        assert calls == ["nut"]

        release.set()
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not button.disabled
        assert not app.query_one("#status-progress").display
