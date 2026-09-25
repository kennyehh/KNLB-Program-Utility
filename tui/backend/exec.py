from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    argv: list[str] | str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(
    argv: list[str] | str,
    *,
    use_shell: bool = False,
    timeout: float | None = None,
) -> CommandResult:
    """Run a command with stdin closed so it can never block on a prompt.

    argv is a list of arguments for direct exec, or a single shell command
    string when use_shell=True (routed through /bin/sh -c).
    """
    try:
        proc = subprocess.run(
            argv,
            shell=use_shell,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return CommandResult(
            argv=argv,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        # text=True above guarantees exc.stdout is str|None at runtime, but
        # TimeoutExpired.stdout is typed bytes|str|None regardless of the
        # caller's text= argument, so narrow it explicitly for the type
        # checker (and to catch it at runtime if that assumption ever breaks).
        assert exc.stdout is None or isinstance(exc.stdout, str)
        return CommandResult(
            argv=argv,
            returncode=-1,
            stdout=(exc.stdout or ""),
            stderr=f"Command timed out after {timeout}s",
        )
    except FileNotFoundError as exc:
        return CommandResult(argv=argv, returncode=127, stdout="", stderr=str(exc))
