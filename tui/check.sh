#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

# Always run from this script's own directory, not the caller's cwd: both
# ruff and basedpyright/pyright discover their config by walking upward from
# the current working directory, and Master_Install_Script/ (the git repo
# root, one level up) has no such config, so invoking either tool from there
# silently loses all config -- basedpyright in particular then floods dozens
# of false-positive reportMissingImports errors instead of the real 0.
if [[ ! -x .venv/bin/python ]]; then
    ./setup.sh
fi

./.venv/bin/pip install -q -r requirements-dev.txt
./.venv/bin/ruff check .
./.venv/bin/basedpyright .
./.venv/bin/pytest -q
