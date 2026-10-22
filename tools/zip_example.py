"""Zip an example project from cmf_examples for uploading to Google Drive.

Leaves out the symlinks to the script (set up by hand, see
cmf_examples/README.txt), the script's outputs and ArcGIS Pro / Python
clutter. The project folder itself is not changed.

Usage (any Python 3.9+, no extra packages):
    python tools/zip_example.py 2026-ven-001 [OUTPUT_ZIP]
The zip goes next to the repository by default (../2026-ven-001.zip).
"""

import argparse
import os
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__", ".ipynb_checkpoints", ".backups", "Index",
             "GpMessages", "ImportLog"}
OUTPUT_DIRS = {"33_Map_Projects", "34_Map_Products_MapAction"}  # keep .gitkeep only


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", help="folder name in cmf_examples")
    parser.add_argument("output", nargs="?", type=Path)
    args = parser.parse_args()
    source = REPO / "cmf_examples" / args.project
    if not source.is_dir():
        raise SystemExit(f"Not found: {source}")
    output = args.output or REPO.parent / f"{args.project}.zip"

    count = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, dirs, files in os.walk(source):
            folder = Path(root)
            name = folder.relative_to(source.parent).as_posix()
            dirs[:] = [d for d in dirs
                       if d not in SKIP_DIRS and not (folder / d).is_symlink()
                       and folder.name not in OUTPUT_DIRS]
            z.write(folder, name + "/")  # keeps empty folders
            for f in files:
                path = folder / f
                if path.is_symlink() or f.endswith((".lock", ".pyc")):
                    continue
                if folder.name in OUTPUT_DIRS and f != ".gitkeep":
                    continue
                z.write(path, f"{name}/{f}")
                count += 1
    print(f"{count} files -> {output} ({output.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
