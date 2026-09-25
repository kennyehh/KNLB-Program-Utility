from backend.critical_packages import is_critical


def test_exact_matches_are_critical():
    for name in ["kernel", "systemd", "bash", "sudo", "NetworkManager", "dnf"]:
        assert is_critical(name) is True


def test_prefixed_variants_are_critical():
    for name in ["kernel-core", "kernel-devel", "grub2-efi-x64", "systemd-resolved", "NetworkManager-wifi"]:
        assert is_critical(name) is True


def test_ordinary_programs_are_not_critical():
    for name in ["strawberry", "firefox", "vim", "htop", "discord", "alacritty"]:
        assert is_critical(name) is False


def test_case_insensitive():
    assert is_critical("KERNEL") is True
    assert is_critical("Kernel-Core") is True


def test_substring_without_hyphen_boundary_is_not_falsely_critical():
    # "kdenlive" contains no critical prefix as a whole-word/hyphen match;
    # make sure prefix matching doesn't get overly loose ("kde" isn't listed,
    # but this guards the boundary logic in general).
    assert is_critical("basement-explorer") is False
