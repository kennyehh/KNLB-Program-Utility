#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from backend.distro import get_distro_info
from backend.logging_setup import SessionLogger
from ui.app import KNLBApp


def main() -> int:
    if os.geteuid() != 0:
        print("This installer must be run as root, e.g.: sudo ./run.sh", file=sys.stderr)
        return 1

    distro = get_distro_info()
    logger = SessionLogger()
    logger.info(
        f"Session started. Distro={distro.distro_name} PackageManager={distro.package_manager}"
    )

    app = KNLBApp(logger=logger, distro=distro)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
