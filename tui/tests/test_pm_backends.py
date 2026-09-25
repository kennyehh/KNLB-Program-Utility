import pytest

from backend.exec import CommandResult
from backend.pm import get_backend


def test_dnf_argv():
    backend = get_backend("dnf")
    assert backend.install_argv("firefox") == ["dnf", "-y", "install", "firefox"]
    assert backend.search_argv("firefox") == ["dnf", "search", "firefox"]


def test_apt_argv():
    backend = get_backend("apt")
    assert backend.install_argv("firefox") == ["apt-get", "-y", "install", "firefox"]
    assert backend.search_argv("firefox") == ["apt-cache", "search", "firefox"]


def test_pacman_argv():
    backend = get_backend("pacman")
    assert backend.install_argv("firefox") == ["pacman", "-S", "--noconfirm", "firefox"]
    assert backend.search_argv("firefox") == ["pacman", "-Ss", "firefox"]


def test_flatpak_argv():
    backend = get_backend("flatpak")
    assert backend.install_argv("org.example.App") == [
        "flatpak",
        "install",
        "-y",
        "flathub",
        "org.example.App",
    ]


def test_snap_argv():
    backend = get_backend("snap")
    assert backend.install_argv("discord") == ["snap", "install", "discord"]


# --- dnf: search_results / exact_match, verified against real `dnf search` output ---


def test_dnf_search_results_exact_match(monkeypatch):
    backend = get_backend("dnf")
    stdout = (
        "Matched fields: name (exact)\n"
        " strawberry.x86_64\tAudio player and music collection organizer\n"
    )
    monkeypatch.setattr(
        "backend.pm.dnf.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("strawberry") == [
        ("strawberry", "Audio player and music collection organizer")
    ]
    assert backend.exact_match("strawberry") == (
        "strawberry",
        "Audio player and music collection organizer",
    )
    assert backend.search("strawberry") is True


def test_dnf_search_results_partial_match(monkeypatch):
    # dnf search straw -> finds strawberry, but "straw" itself isn't a package
    backend = get_backend("dnf")
    stdout = "Matched fields: name\n strawberry.x86_64\tAudio player and music collection organizer\n"
    monkeypatch.setattr(
        "backend.pm.dnf.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("straw") == [
        ("strawberry", "Audio player and music collection organizer")
    ]
    # "straw" has no exact-name match even though it found a fuzzy result
    assert backend.exact_match("straw") is None


def test_dnf_search_results_not_found(monkeypatch):
    backend = get_backend("dnf")
    monkeypatch.setattr(
        "backend.pm.dnf.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout="No matches found.\n", stderr=""),
    )
    assert backend.search_results("zzz-nonexistent") == []
    assert backend.search("zzz-nonexistent") is False


def test_dnf_search_results_multiple_matches(monkeypatch):
    backend = get_backend("dnf")
    stdout = (
        "Matched fields: name\n"
        " nut.x86_64\tNetwork UPS Tools\n"
        " nut-devel.x86_64\tDevelopment files for nut\n"
    )
    monkeypatch.setattr(
        "backend.pm.dnf.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("nut") == [
        ("nut", "Network UPS Tools"),
        ("nut-devel", "Development files for nut"),
    ]
    assert backend.exact_match("nut") == ("nut", "Network UPS Tools")


# --- apt: documented "pkgname - description" format (unverified: no apt-cache on this machine) ---


def test_apt_search_results(monkeypatch):
    backend = get_backend("apt")
    stdout = "nut - Network UPS Tools - core system\nnut-cgi - network UPS tools CGI\n"
    monkeypatch.setattr(
        "backend.pm.apt.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("nut") == [
        ("nut", "Network UPS Tools - core system"),
        ("nut-cgi", "network UPS tools CGI"),
    ]
    assert backend.exact_match("nut") == ("nut", "Network UPS Tools - core system")


# --- pacman: documented "repo/pkgname version" + indented description format (unverified) ---


def test_pacman_search_results(monkeypatch):
    backend = get_backend("pacman")
    stdout = "core/nut 2.8.0-1\n    Network UPS Tools\n"
    monkeypatch.setattr(
        "backend.pm.pacman.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("nut") == [("nut", "Network UPS Tools")]
    assert backend.exact_match("nut") == ("nut", "Network UPS Tools")


# --- flatpak: verified against real `flatpak search` output (tab-separated, no header) ---


def test_flatpak_search_results(monkeypatch):
    backend = get_backend("flatpak")
    stdout = (
        "Firefox\tWeb Browser\torg.mozilla.firefox\t155.0\tstable\tfedora,flathub\n"
        "Firefox\tWeb Browser\torg.mozilla.Firefox\t124.0\tstable\tfedora\n"
    )
    monkeypatch.setattr(
        "backend.pm.flatpak.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("firefox") == [
        ("org.mozilla.firefox", "Web Browser"),
        ("org.mozilla.Firefox", "Web Browser"),
    ]
    # exact_match compares against the app ID's last segment, since a typed
    # term like "firefox" never equals the full app ID directly.
    assert backend.exact_match("firefox") == ("org.mozilla.firefox", "Web Browser")


# --- snap: verified against real `snap find` output (header row + aligned columns) ---


def test_snap_search_results(monkeypatch):
    backend = get_backend("snap")
    stdout = (
        "Name                       Version             Publisher         Notes  Summary\n"
        "firefox                    156.0.1-1           mozilla**         -      Mozilla Firefox web browser\n"
        "firefox-kiosk              0.1                 scout208          -      firefox example kiosk\n"
    )
    monkeypatch.setattr(
        "backend.pm.snap.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.search_results("firefox") == [
        ("firefox", "Mozilla Firefox web browser"),
        ("firefox-kiosk", "firefox example kiosk"),
    ]
    assert backend.exact_match("firefox") == ("firefox", "Mozilla Firefox web browser")


# --- list_installed / uninstall_argv, for the Uninstaller page ---


def test_dnf_list_installed(monkeypatch):
    backend = get_backend("dnf")
    stdout = "strawberry\tAudio player and music collection organizer\nhtop\tInteractive process viewer\n"
    monkeypatch.setattr(
        "backend.pm.dnf.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.list_installed() == [
        ("strawberry", "Audio player and music collection organizer"),
        ("htop", "Interactive process viewer"),
    ]
    assert backend.uninstall_argv("strawberry") == ["dnf", "-y", "remove", "strawberry"]


def test_dnf_list_installed_command_failure(monkeypatch):
    backend = get_backend("dnf")
    monkeypatch.setattr(
        "backend.pm.dnf.run_command",
        lambda argv: CommandResult(argv=argv, returncode=1, stdout="", stderr="error"),
    )
    assert backend.list_installed() == []


def test_apt_list_installed(monkeypatch):
    backend = get_backend("apt")
    calls = []

    def fake_run(argv):
        calls.append(argv)
        if argv[0] == "apt-mark":
            return CommandResult(argv=argv, returncode=0, stdout="strawberry\nhtop\n", stderr="")
        return CommandResult(
            argv=argv,
            returncode=0,
            stdout="strawberry\tAudio player and music collection organizer\nhtop\tInteractive process viewer\n",
            stderr="",
        )

    monkeypatch.setattr("backend.pm.apt.run_command", fake_run)
    assert backend.list_installed() == [
        ("strawberry", "Audio player and music collection organizer"),
        ("htop", "Interactive process viewer"),
    ]
    # a single batched dpkg-query call covering all names, not one per package
    assert len(calls) == 2
    assert backend.uninstall_argv("strawberry") == ["apt-get", "-y", "remove", "--autoremove", "strawberry"]


def test_apt_list_installed_no_manual_packages(monkeypatch):
    backend = get_backend("apt")
    monkeypatch.setattr(
        "backend.pm.apt.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout="", stderr=""),
    )
    assert backend.list_installed() == []


def test_pacman_list_installed(monkeypatch):
    backend = get_backend("pacman")
    stdout = (
        "Name            : strawberry\n"
        "Version         : 1.0.20-1\n"
        "Description     : Audio player and music collection organizer\n"
        "\n"
        "Name            : htop\n"
        "Version         : 3.3.0-1\n"
        "Description     : Interactive process viewer\n"
    )
    monkeypatch.setattr(
        "backend.pm.pacman.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout=stdout, stderr=""),
    )
    assert backend.list_installed() == [
        ("strawberry", "Audio player and music collection organizer"),
        ("htop", "Interactive process viewer"),
    ]
    assert backend.uninstall_argv("strawberry") == ["pacman", "-R", "-s", "--noconfirm", "strawberry"]


# --- is_installed, for the "already installed" green highlight ---


def test_dnf_is_installed(monkeypatch):
    backend = get_backend("dnf")
    calls = []

    def fake_run(argv):
        calls.append(argv)
        return CommandResult(argv=argv, returncode=0 if argv[-1] == "strawberry" else 1, stdout="", stderr="")

    monkeypatch.setattr("backend.pm.dnf.run_command", fake_run)
    assert backend.is_installed("strawberry") is True
    assert backend.is_installed("not-installed") is False
    assert calls[0] == ["rpm", "-q", "strawberry"]


def test_apt_is_installed(monkeypatch):
    backend = get_backend("apt")
    monkeypatch.setattr(
        "backend.pm.apt.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout="", stderr=""),
    )
    assert backend.is_installed("bash") is True


def test_pacman_is_installed(monkeypatch):
    backend = get_backend("pacman")
    monkeypatch.setattr(
        "backend.pm.pacman.run_command",
        lambda argv: CommandResult(argv=argv, returncode=1, stdout="", stderr="not found"),
    )
    assert backend.is_installed("nut") is False


def test_flatpak_is_installed(monkeypatch):
    backend = get_backend("flatpak")
    monkeypatch.setattr(
        "backend.pm.flatpak.run_command",
        lambda argv: CommandResult(argv=argv, returncode=0, stdout="", stderr=""),
    )
    assert backend.is_installed("org.mozilla.firefox") is True


def test_snap_is_installed(monkeypatch):
    backend = get_backend("snap")
    monkeypatch.setattr(
        "backend.pm.snap.run_command",
        lambda argv: CommandResult(argv=argv, returncode=1, stdout="", stderr="error"),
    )
    assert backend.is_installed("firefox") is False


def test_get_backend_unknown_raises():
    with pytest.raises(ValueError):
        get_backend("nonexistent-pm")
