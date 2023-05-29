#!/usr/bin/env python

import shutil
from pathlib import Path

from tungstenkit._internal import demo_server

frontend_dir_in_proj = Path(__file__).parent.parent / "frontend" / "out"
if not frontend_dir_in_proj.is_dir():
    raise NotADirectoryError(frontend_dir_in_proj)

frontend_dir_in_pkg = Path(demo_server.__file__).parent / "frontend"
if frontend_dir_in_pkg.exists():
    inp = input(f"Remove directory '{frontend_dir_in_pkg}'? (y/n) ")
    if inp == "y":
        shutil.rmtree(frontend_dir_in_pkg)
    else:
        exit(1)

shutil.copytree(frontend_dir_in_proj, frontend_dir_in_pkg)

print(f"Copied {frontend_dir_in_proj} to {frontend_dir_in_pkg}")
