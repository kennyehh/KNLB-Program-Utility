from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from backend.exec import CommandResult, run_command


class PackageManagerBackend(ABC):
    name: ClassVar[str]

    @abstractmethod
    def search_argv(self, term: str) -> list[str]: ...

    @abstractmethod
    def install_argv(self, term: str) -> list[str]: ...

    def found_in_search(self, result: CommandResult, term: str) -> bool:
        return result.ok and term.lower() in result.stdout.lower()

    def search_results(self, term: str) -> list[tuple[str, str]]:
        """All (package_name, description) matches for a broad/fuzzy search,
        e.g. the full output of `dnf search <term>`. Backends without a real
        results parser fall back to a single unnamed result using the raw
        term as the name, if found_in_search is True."""
        result = run_command(self.search_argv(term))
        if self.found_in_search(result, term):
            return [(term, "")]
        return []

    def exact_match(self, term: str) -> tuple[str, str] | None:
        """The single result whose name matches term exactly, if any."""
        term_lower = term.lower()
        for name, description in self.search_results(term):
            if name.lower() == term_lower:
                return name, description
        return None

    def search(self, term: str) -> bool:
        return self.exact_match(term) is not None

    def install(self, term: str) -> CommandResult:
        return run_command(self.install_argv(term))

    def list_installed(self) -> list[tuple[str, str]]:
        """All (package_name, description) pairs for user-installed programs.
        Backends without a real implementation return an empty list."""
        return []

    def uninstall_argv(self, term: str) -> list[str]:
        raise NotImplementedError(f"{self.name} does not support uninstall")

    def uninstall(self, term: str) -> CommandResult:
        return run_command(self.uninstall_argv(term))

    def is_installed(self, term: str) -> bool:
        """Whether term is already installed on this system right now
        (distinct from search()/exact_match(), which check availability in
        the repos). Backends without a real implementation return False."""
        return False


_REGISTRY: dict[str, PackageManagerBackend] = {}


def register(backend: PackageManagerBackend) -> PackageManagerBackend:
    _REGISTRY[backend.name] = backend
    return backend


def get_backend(pm_name: str) -> PackageManagerBackend:
    try:
        return _REGISTRY[pm_name]
    except KeyError:
        raise ValueError(f"Unknown package manager backend: {pm_name!r}") from None


# Import submodules for their registration side effects. Must stay after the
# definitions above since each submodule imports PackageManagerBackend/register
# from this package.
from backend.pm import apt, dnf, flatpak, pacman, snap  # noqa: F401
