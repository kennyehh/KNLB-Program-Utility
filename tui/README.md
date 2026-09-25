# KNLB Installer (Phase 2 TUI)

A Textual-based terminal UI that replaces phase 1's per-program `install_*.sh`
scripts with live package-manager search and on-demand install/uninstall.
"Installer", "Uninstaller", and "Fonts" buttons below the banner switch
between the three panes. The Installer and Uninstaller each show a live side
panel of the current selections (name + description), which persist across
filtering and only clear on deselect, install/uninstall, or Reset.

## Setup

    ./setup.sh

Creates a `.venv/` and installs dependencies from `requirements.txt`.

## Run

    sudo ./run.sh

Must be run as root, matching phase 1's convention (installs call
`dnf`/`apt`/`pacman`/`flatpak`/`snap` directly with no `sudo` of their own).

## Tests

    ./.venv/bin/pip install -r requirements-dev.txt
    ./.venv/bin/pytest

Covers the `backend/` modules (distro detection, package-manager backends,
catalog loading, prerequisite handling, font install, uninstall listing, and
the critical-package blocklist). The Textual UI itself (`ui/`) is otherwise
verified by running the app.

## Diagnostics

    ./check.sh

Runs `ruff check .`, `basedpyright .`, and the test suite together. **Always
use this script (or `cd tui` first) rather than invoking `ruff`/`basedpyright`
directly from `Master_Install_Script/`** (the repo root, one level up): both
tools discover their config by walking upward from the current working
directory, never downward, so running them from the repo root silently finds
no config at all. For ruff this just means different default rules; for
basedpyright it's worse — confirmed live, it floods 94 errors including 29
false-positive `reportMissingImports` (`textual`/`pytest`/`rich` "not found",
even though they're installed) instead of the real 0, because it falls back
to some environment other than `tui/.venv`. `check.sh` runs from its own
directory regardless of caller cwd, exactly like `setup.sh`/`run.sh` already
do, so this can't happen by accident.

Lint pass (no separate ruff config; ruff's own defaults). A couple of findings
are intentionally suppressed inline with a `# noqa` and a reason rather than
"fixed" — a broad `except Exception` in the font downloader (it wraps a
pluggable callable that can fail in many ways) and a naive `datetime.now()`
used only for a human-readable log filename.

Type checking runs in `basic` mode (`pyrightconfig.json`, which also pins
`venvPath`/`venv` explicitly to `tui/.venv` rather than relying on
basedpyright's auto-detection) rather than basedpyright's own stricter
default: the default mode reports 16 errors and 529 warnings on this
codebase, but the overwhelming majority are basedpyright-specific strictness
rules (`reportUnknownMemberType`, `reportUnusedCallResult`, `reportAny`, etc.)
firing against Textual's loosely and incompletely typed widget API, not real
bugs — `basic` mode surfaces the same 4 genuine issues found under the
default mode and nothing else. When `exc.stdout`/`exc.stderr` from a caught
`subprocess.TimeoutExpired` are used, narrow them with
`assert exc.stdout is None or isinstance(exc.stdout, str)` rather than a bare
`cast` — `TimeoutExpired.stdout`/`.stderr` are typed `bytes | str | None`
regardless of whether the original call passed `text=True`, and the assert
also catches it at runtime if that assumption ever breaks (see
`backend/exec.py`).

## Layout

- `backend/` — pure logic, no Textual imports: distro/PM detection, per-backend
  package manager search/install/uninstall, prerequisite installation
  (flatpak/snapd/dnf copr plugin), the curated catalog loader, font URL
  install, session logging, and a critical-package blocklist for the
  uninstaller. A search miss is reported as a failure — there is no
  manual/custom command entry, since the app runs as root and free-form shell
  input would be arbitrary command execution as root.
- `ui/` — the Textual app, screens, and widgets. Imports `backend/`, never the
  reverse.
- `data/catalog.json` — curated well-known-programs catalog, seeded from
  `fedora_reinstall/README.md`'s existing program list.
- `logs/` — created at runtime, one timestamped file per session (gitignored).
