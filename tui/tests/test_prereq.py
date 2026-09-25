from backend.exec import CommandResult
from backend.prereq import PrereqSpec, PrereqType, ensure, is_satisfied


def test_is_satisfied_flatpak_true():
    assert is_satisfied(PrereqSpec(PrereqType.FLATPAK), which=lambda n: "/usr/bin/flatpak")


def test_is_satisfied_flatpak_false():
    assert not is_satisfied(PrereqSpec(PrereqType.FLATPAK), which=lambda n: None)


def test_ensure_flatpak_installs_and_adds_remote(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return CommandResult(argv=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("backend.prereq.run_command", fake_run)
    monkeypatch.setattr("backend.prereq.shutil.which", lambda n: None)

    result = ensure(PrereqSpec(PrereqType.FLATPAK))
    assert result.ok
    assert calls[0] == ["dnf", "-y", "install", "flatpak"]
    assert calls[1][:2] == ["flatpak", "remote-add"]


def test_ensure_snap_installs_and_enables_socket(monkeypatch, tmp_path):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return CommandResult(argv=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("backend.prereq.run_command", fake_run)
    monkeypatch.setattr("backend.prereq.shutil.which", lambda n: None)
    monkeypatch.setattr("backend.prereq.Path", lambda p: tmp_path / "snap-does-not-exist")

    result = ensure(PrereqSpec(PrereqType.SNAP))
    assert result.ok
    assert calls[0] == ["dnf", "-y", "install", "snapd"]
    assert calls[1] == ["systemctl", "enable", "--now", "snapd.socket"]
    assert calls[2][:2] == ["ln", "-s"]


def test_ensure_copr_enables_repo(monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        if argv == ["dnf", "copr", "--help"]:
            # Simulate the plugin not being present yet, so ensure() proceeds
            # to install it and enable the repo.
            return CommandResult(argv=argv, returncode=1, stdout="", stderr="")
        return CommandResult(argv=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("backend.prereq.run_command", fake_run)

    result = ensure(PrereqSpec(PrereqType.COPR, repo="lilay/topgrade"))
    assert result.ok
    assert calls[0] == ["dnf", "copr", "--help"]
    assert calls[1] == ["dnf", "-y", "install", "dnf-plugins-core"]
    assert calls[2] == ["dnf", "-y", "copr", "enable", "lilay/topgrade"]


def test_ensure_already_satisfied_is_noop(monkeypatch):
    called = False

    def fake_run(argv, **kwargs):
        nonlocal called
        called = True
        return CommandResult(argv=argv, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("backend.prereq.run_command", fake_run)
    monkeypatch.setattr("backend.prereq.shutil.which", lambda n: "/usr/bin/flatpak")

    result = ensure(PrereqSpec(PrereqType.FLATPAK))
    assert result.ok
    assert called is False
