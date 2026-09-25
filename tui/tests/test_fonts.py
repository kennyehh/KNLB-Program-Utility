import os
import pwd
import zipfile
from pathlib import Path

from backend.exec import CommandResult
from backend.fonts import (
    FontOwner,
    default_font_dir,
    install_font_from_url,
    invoking_user,
)


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


def test_invoking_user_from_sudo_env():
    me = pwd.getpwuid(os.getuid())
    owner = invoking_user({"SUDO_UID": str(me.pw_uid)})
    if me.pw_uid == 0:
        assert owner is None
    else:
        assert owner == FontOwner(name=me.pw_name, uid=me.pw_uid, gid=me.pw_gid, home=Path(me.pw_dir))


def test_invoking_user_absent_or_invalid():
    assert invoking_user({}) is None
    assert invoking_user({"SUDO_UID": "not-a-number"}) is None
    assert invoking_user({"SUDO_UID": "0"}) is None


def test_install_font_for_invoking_user_chowns_and_runs_fc_cache_as_them(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    owner = FontOwner(name="someone", uid=os.getuid(), gid=os.getgid(), home=home)
    dest_dir = default_font_dir("https://example.com/UserFont.zip", base=home / ".local" / "share" / "fonts")
    calls = []

    def recording_run(argv):
        calls.append(argv)
        return _fake_run(argv)

    def fake_downloader(url, dest):
        with zipfile.ZipFile(dest, "w") as zf:
            zf.writestr("UserFont-Regular.ttf", b"fake-font-bytes")

    result = install_font_from_url(
        "https://example.com/UserFont.zip",
        dest_dir=dest_dir,
        downloader=fake_downloader,
        run=recording_run,
        owner=owner,
    )
    assert result.ok
    assert dest_dir == home / ".local" / "share" / "fonts" / "UserFont"
    assert (dest_dir / "UserFont-Regular.ttf").exists()
    assert (home / ".local").stat().st_uid == owner.uid
    assert calls == [["runuser", "-u", "someone", "--", "fc-cache", "-f", str(dest_dir)]]
