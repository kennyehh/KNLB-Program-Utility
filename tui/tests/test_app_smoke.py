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
