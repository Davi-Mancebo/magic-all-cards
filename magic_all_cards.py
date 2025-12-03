from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src_path() -> None:
    if getattr(sys, "frozen", False):
        # When frozen, make sure the directory that contains the executable is
        # not masking the bundled package, but PyInstaller already exposes the
        # package via sys._MEIPASS so no extra path is required.
        exec_dir = Path(sys.argv[0]).resolve().parent
        exec_dir_str = str(exec_dir)
        if exec_dir_str in sys.path:
            sys.path.remove(exec_dir_str)
        return

    project_root = Path(__file__).resolve().parent
    project_root_str = str(project_root)
    src_dir = project_root / "src"

    if project_root_str in sys.path:
        sys.path.remove(project_root_str)

    src_dir_str = str(src_dir)
    if src_dir_str not in sys.path:
        sys.path.insert(0, src_dir_str)


_bootstrap_src_path()

from magic_all_cards.gui import main


if __name__ == "__main__":
    main()
