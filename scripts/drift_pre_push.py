from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    check = subprocess.run(
        ["drift", "check", "--fail-on", "high"],
        check=False,
        env=env,
    )
    return check.returncode


if __name__ == "__main__":
    sys.exit(main())
