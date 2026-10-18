"""Rebuild the test data in cmf_examples/2026-ven-001 from the live project.

Copies each file listed in test_data_manifest.txt (paths relative to the
project root) from the live Nextcloud project into the test copy. The live
project is only read, never written to. Files already present with the same
size are skipped.

Usage (any Python 3.9+, no extra packages):
    python tools/copy_test_data.py [LIVE_PROJECT_FOLDER]
"""

import shutil
import sys
from pathlib import Path

DEFAULT_LIVE = Path.home() / "Nextcloud/Projects/2026/2026-ven-001"
REPO = Path(__file__).resolve().parent.parent
TEST_PROJECT = REPO / "cmf_examples/2026-ven-001"
MANIFEST = Path(__file__).resolve().parent / "test_data_manifest.txt"


def main():
    live = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_LIVE
    if not live.is_dir():
        raise SystemExit(f"Live project not found: {live}")

    copied = skipped = 0
    missing = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        source, target = live / line, TEST_PROJECT / line
        if not source.is_file():
            missing.append(line)
            continue
        if target.is_file() and target.stat().st_size == source.stat().st_size:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    print(f"Copied {copied}, already up to date {skipped}.")
    if missing:
        print("Not found in the live project:")
        for line in missing:
            print("  -", line)


if __name__ == "__main__":
    main()
