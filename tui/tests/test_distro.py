from backend.distro import detect_distro, detect_package_manager, get_distro_info


def test_detect_distro_fedora(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text('NAME="Fedora Linux"\nID=fedora\nVERSION_ID=44\n')
    assert detect_distro(os_release) == "Fedora"


def test_detect_distro_unknown(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text('NAME="MysteryOS"\n')
    assert detect_distro(os_release) == "Unknown"


def test_detect_distro_missing_file(tmp_path):
    assert detect_distro(tmp_path / "does-not-exist") == "Unknown"


def test_detect_package_manager_prefers_first_match():
    def fake_which(name):
        return f"/usr/bin/{name}" if name == "dnf" else None

    pm_name, pm_path = detect_package_manager(which=fake_which)
    assert pm_name == "dnf"
    assert pm_path == "/usr/bin/dnf"


def test_detect_package_manager_none_found():
    pm_name, pm_path = detect_package_manager(which=lambda name: None)
    assert pm_name == ""
    assert pm_path == ""


def test_get_distro_info(tmp_path):
    os_release = tmp_path / "os-release"
    os_release.write_text("ID=ubuntu\nNAME=Ubuntu\n")
    info = get_distro_info(
        os_release, which=lambda name: "/usr/bin/apt" if name == "apt" else None
    )
    assert info.distro_name == "Ubuntu"
    assert info.package_manager == "apt"
