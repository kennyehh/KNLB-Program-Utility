from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from backend.exec import CommandResult

DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


class SessionLogger:
    """Creates one timestamped log file per TUI session."""

    def __init__(self, log_dir: Path = DEFAULT_LOG_DIR):
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")  # noqa: DTZ005 - local time is intended for a human-readable filename
        self.path = log_dir / f"session-{timestamp}.log"

        self._logger = logging.getLogger(f"knlb_tui.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = logging.FileHandler(self.path)
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self._logger.addHandler(handler)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    def log_command(self, result: CommandResult) -> None:
        status = "OK" if result.ok else "FAILED"
        argv_str = " ".join(result.argv) if isinstance(result.argv, list) else result.argv
        self._logger.info(f"[{status}] {argv_str} (rc={result.returncode})")
        if result.stderr:
            self._logger.info(f"  stderr: {result.stderr.strip()}")

    def log_install_batch(self, outcomes: list) -> None:
        """Called once per 'Install Selected' press."""
        self._logger.info("--- Install Selected batch ---")
        for outcome in outcomes:
            status = "OK" if getattr(outcome, "ok", False) else "FAILED"
            name = getattr(outcome, "name", str(outcome))
            message = getattr(outcome, "message", "")
            self._logger.info(f"[{status}] {name}: {message}")
        self._logger.info("--- End batch ---")
