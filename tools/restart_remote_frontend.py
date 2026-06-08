#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import time


PATTERN = "python -m uvicorn server.phys_backend"
ROOT = "/root/autodl-tmp/ustc26mm"


def main() -> None:
    out = subprocess.check_output(["ps", "-eo", "pid,args"], text=True)
    for line in out.splitlines():
        if PATTERN in line and "grep" not in line:
            pid = int(line.strip().split(None, 1)[0])
            os.kill(pid, signal.SIGTERM)
    time.sleep(2)
    subprocess.Popen(
        ["bash", "-lc", f"cd {ROOT} && nohup ./start_frontend.sh > frontend.log 2>&1 < /dev/null &"],
        start_new_session=True,
    )
    time.sleep(3)
    print(subprocess.check_output(["bash", "-lc", "ps -ef | grep 'uvicorn server.phys_backend' | grep -v grep"], text=True))


if __name__ == "__main__":
    main()
