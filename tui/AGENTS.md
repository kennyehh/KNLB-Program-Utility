# General Guidelines for the Phase 2 TUI

## Intention
 - Phase 2 replaces the `install_*.sh` script-per-program model in `fedora_reinstall/` with a terminal UI that searches the native package manager directly and installs/uninstalls on demand
 - This does not modify or depend on `fedora_reinstall/`; it is a from-scratch reimplementation of the install logic, exposed through an interactive UI

## Navigation
 - The top of the TUI displays a centered title using ASCII displaying the letters: KNLB
 - Below the banner, "Installer", "Uninstaller", and "Fonts" are buttons (not a separate screen each) that switch which pane is shown below them; the banner and these nav buttons stay persistent. The active pane's button is visually highlighted.

## Scope: Installer (per top-level AGENTS.md "Possible Upgrades")
 - Detect the current Linux distribution and its native package manager
 - Present a list of well-known/common programs the user can select from
 - Allow the user to type in an arbitrary program name. A plain name (e.g. `nut`) does an exact-name lookup and adds it pre-selected if found. A leading `~` (e.g. `~nut`) instead runs a broad/fuzzy search (`dnf search`, `apt-cache search`, `pacman -Ss`, or whatever the distro's equivalent is) and adds every match to the list, unselected, so the user can review and pick which ones (if any) to install
 - For either path, search the native package manager for the program and install it if found, showing the real description text from the package manager alongside the name
 - The default is always to search the distro's own configured default repos — never a third-party one automatically. If not found there, tell the user plainly (e.g. "not found — you may have to add additional repos or check the installation instructions") rather than a bare "not found", since that actual next step is usually enabling another repo or reading the program's own install docs. This applies uniformly to catalog entries and user-typed searches alike, rather than accepting a manually-typed install command. Arbitrary shell/command entry is explicitly out of scope: the app runs as root, so free-form input from that field would be arbitrary command execution as root (confirmed as a real issue after testing: a manual entry of `touch /path/to/file` executed successfully). No shell is ever invoked on user-typed text
 - Filtering the list never changes what's selected, including for entries currently hidden by the filter — selections are tracked independently of what the filter happens to be showing at any moment, and persist until the item is explicitly deselected, "Install Selected" is run, or "Reset" is pressed (confirmed as a real bug after testing: filtering, or filtering-then-clearing, used to silently drop existing selections)
 - A side panel next to the program list shows the current selections live (name + description), updating immediately as items are checked/unchecked, and clearing an item the moment it's deselected, reset, or installed
 - "Install Selected" runs the install for every checked program; "Reset" clears all program selections (including any ad hoc search results) and the filter/search text, and also triggers a full rescan of installed status (see below) in case something changed outside the app since the last scan
 - A program already installed on the system (checked via each backend's `is_installed`, e.g. `rpm -q`/`dpkg -s`/`pacman -Q`/`flatpak info`/`snap list` against the entry's specific resolved package/backend, not "installed by any means whatsoever") is shown in green. This stays live: it updates right after a successful install, clears if the program is later removed from the Uninstaller, and a full rescan (replacing the whole known-installed set, not just merging in new finds, so something uninstalled outside the app also correctly loses its green) runs on startup and every time Reset is pressed
 - A configs sub-menu (applying program config files, e.g. alacritty.toml) is deferred out of scope for now

## Scope: Uninstaller
 - Lists the user's currently-installed programs using the distro-appropriate command: `dnf repoquery --userinstalled` / `apt-mark showmanual` / `pacman -Qe`
 - Descriptions are fetched via a single batched query per distro, not one search call per installed package — a real system can easily have 500+ user-installed packages, and doing that many sequential subprocess calls would be far too slow. dnf uses `repoquery --userinstalled --qf "%{name}\t%{summary}\n"` (one fast local rpmdb query); apt batches every name through one `dpkg-query` call; pacman uses `pacman -Qei`'s per-package info blocks in one call
 - A best-effort blocklist (`backend/critical_packages.py`) hides obviously-critical system packages (kernel, bootloader, init system, core libc/auth, etc.) from the list entirely, to reduce the chance of catastrophically breaking the system. This is not exhaustive — it's insurance against the most severe accidents, not a guarantee
 - Allow the user to select multiple programs the same way as the Installer's list (filter box + checkboxes, with the same persistent-selection-through-filtering behavior and a live side panel of name + description), with an "Uninstall Selected" button and a "Reset" button
 - Uninstalling removes now-unneeded dependencies along with the selected package(s), not just the exact package: dnf's `remove` already does this by default, apt uses `remove --autoremove`, pacman uses `-Rs`
 - Before anything actually runs, a confirmation modal lists the exact program names about to be removed; the user must explicitly confirm or cancel. This is a deliberately asymmetric safety step compared to the Installer (which runs immediately) since uninstalling — especially combined with dependency cleanup, and running as root — is comparatively more destructive and harder to reverse
 - The list refreshes after an uninstall run so removed programs disappear from it, and "Reset" also triggers a fresh rescan of the whole list (a real `list_installed()` call, not just a re-render of cached data), in case something was installed/removed outside the app since the last load
 - A program that also appears in the Installer's catalog (matched by its resolved per-distro package name, not the catalog's display name — e.g. catalog "sshPilot" resolves to package "sshpilot") has its name shown in light blue, distinct from the Installer's plain green for "already installed". This is not "already installed" (everything here already is that) — it's "this is also one of the curated catalog programs"
 - The checkbox "X" indicator itself is always a plain, explicit green when checked, in both the Installer and Uninstaller, regardless of what color the program's own name is styled — the two are deliberately decoupled (`ui/widgets/colorable_selection_list.py`, needed because Textual's SelectionList always renders its own CSS color "on top of" any inline style embedded in an option's prompt text, so per-row name coloring has to go through real CSS component classes instead)

## Scope: Fonts
 - A dedicated section, separate from the Installer, for font installation only — not bundled into "Install Selected"
 - The user pastes the URL for a font zip file, which is downloaded and extracted, matching the flow in fedora_reinstall/configs/fonts_install.sh, with a live preview of where it will be installed
 - Provide the user the option to use the default location for fonts in their distro, or enter their own custom location
 - The default location is `$HOME/.local/share/fonts/$FONT_NAME` for the user who launched the app via `sudo` (looked up from `SUDO_UID`/`PKEXEC_UID`), not root's `/root/...`. Anything created inside that user's home is chowned to them, and `fc-cache` runs as them (`runuser -u <user>`) so the fonts land in their own font cache
 - "Install Font" installs the pasted URL; "Reset" clears the font fields back to defaults

## Specifics
 - Language: Python, using Textual for the TUI (handles Tab/Shift+Tab focus, checkboxes, and buttons natively rather than hand-rolling navigation on top of stdlib curses)
 - Keep distro/package-manager detection and search logic isolated per backend (dnf/apt/pacman) so support for a new distro doesn't touch UI code
 - Missing prerequisite package managers/plugins (flatpak, snapd, dnf copr plugin, etc.) required by a selected install are auto-installed silently before the dependent command runs, mirroring phase 1's required_pm/ behavior
 - The curated "well-known/common programs" catalog lives in an external data file (JSON/YAML) mapping program name to per-distro package name, not hardcoded in Python. Most entries include dnf/apt/pacman search terms (safe since these are essentially universal FOSS package names); a few (Moonlight, sshPilot, Topgrade) are intentionally dnf-only with a `_note` explaining why (Fedora-COPR-only or inconsistent naming elsewhere) rather than guessing at unverifiable apt/pacman names
 - Make sure that any installation/uninstallation command is run without requiring user input once it is committed
 - A status bar above the output log shows when a job (Install Selected, Uninstall Selected, Install Font) is running: a spinner, the current step (e.g. "Installing nut (2/5)..."), and a progress bar (indeterminate for fonts). Only one job runs at a time — while one is running, all three job buttons are disabled and any further attempt is refused
 - Allow the user to navigate the TUI using the keyboard: tab to move between fields, shift+tab to move back between fields, space to select/deselect a field, enter to confirm an option, arrow keys to navigate within fields
 - Create a timestamped log file for each TUI session
 - Add to the log file after each "install selected"/"uninstall selected" process is run
 - Check each install command for dependencies like repositories
