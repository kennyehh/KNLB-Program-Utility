from __future__ import annotations

# Best-effort safety net, not exhaustive: package name prefixes considered too
# risky to offer for uninstall via this tool (bootloader, kernel, init system,
# core libc/auth, and other packages whose removal can render the system
# unbootable or unusable). Matched as an exact name or a "<prefix>-..." name,
# covering both Fedora-style (kernel, grub2) and Debian-style (linux-image,
# grub-pc) naming conventions since this list applies across all backends.
CRITICAL_PACKAGE_PREFIXES = (
    "kernel",
    "linux-image",
    "linux-headers",
    "grub2",
    "grub-pc",
    "grub-efi",
    "grubby",
    "shim-ia32",
    "shim-x64",
    "dracut",
    "efibootmgr",
    "plymouth",
    "systemd",
    "dbus",
    "dnf",
    "apt",
    "pacman",
    "rpm",
    "glibc",
    "bash",
    "coreutils",
    "util-linux",
    "filesystem",
    "setup",
    "base",
    "base-devel",
    "shadow-utils",
    "pam",
    "sudo",
    "NetworkManager",
)


def is_critical(name: str) -> bool:
    lowered = name.lower()
    for prefix in CRITICAL_PACKAGE_PREFIXES:
        prefix_lower = prefix.lower()
        if lowered == prefix_lower or lowered.startswith(prefix_lower + "-"):
            return True
    return False
