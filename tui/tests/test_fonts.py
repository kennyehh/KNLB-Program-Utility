import zipfile
from pathlib import Path

from backend.exec import CommandResult
from backend.fonts import default_font_dir, install_font_from_url


def test_default_font_dir_strips_zip():
    url = "https://example.com/fonts/MyFont.zip"
    dest = default_font_dir(url, base=Path("/tmp/fonts-base"))
    assert dest == Path("/tmp/fonts-base/MyFont")


def test_default_font_dir_with_query_string():
    url = "https://example.com/fonts/MyFont.zip?x=1"
    dest = default_font_dir(url, base=Path("/tmp/fonts-base"))
    assert dest.name == "MyFont"


def _fake_run(argv):
    return CommandResult(argv=argv, returncode=0, stdout="", stderr="")


def test_install_font_success(tmp_path):
    url = "https://example.com/fonts/TestFont.zip"

    def fake_downloader(url, dest):
        with zipfile.ZipFile(dest, "w") as zf:
            zf.writestr("TestFont-Regular.ttf", b"fake-font-bytes")

    result = install_font_from_url(
        url, dest_dir=tmp_path / "TestFont", downloader=fake_downloader, run=_fake_run
    )
    assert result.ok
    assert (tmp_path / "TestFont" / "TestFont-Regular.ttf").exists()
    assert not (tmp_path / "TestFont" / "font.zip").exists()


def test_install_font_download_failure_cleans_up(tmp_path):
    def failing_downloader(url, dest):
        raise OSError("network down")

    dest_dir = tmp_path / "BadFont"
    result = install_font_from_url(
        "https://example.com/BadFont.zip",
        dest_dir=dest_dir,
        downloader=failing_downloader,
        run=_fake_run,
    )
    assert not result.ok
    assert not dest_dir.exists()


def test_install_font_extract_failure_cleans_up(tmp_path):
    def fake_downloader(url, dest):
        dest.write_bytes(b"not a real zip")

    dest_dir = tmp_path / "CorruptFont"
    result = install_font_from_url(
        "https://example.com/CorruptFont.zip",
        dest_dir=dest_dir,
        downloader=fake_downloader,
        run=_fake_run,
    )
    assert not result.ok
    assert not dest_dir.exists()
