"""Fill in the test data in cmf_examples/2026-ven-001 from the live project.

Copies each file listed in test_data_manifest.txt (paths relative to the
project root) from the live Nextcloud project into the test copy. The live
project is only read, never written to.

By default only missing files are copied. With --refresh, files whose size
differs from the live copy are replaced too, except the files in
LOCAL_CHANGES, which are deliberately different in the test copy.

Usage (any Python 3.9+, no extra packages):
    python tools/copy_test_data.py [--refresh] [LIVE_PROJECT_FOLDER]
"""

import argparse
import shutil
from pathlib import Path

DEFAULT_LIVE = Path.home() / "Nextcloud/Projects/2026/2026-ven-001"
REPO = Path(__file__).resolve().parent.parent
TEST_PROJECT = REPO / "cmf_examples/2026-ven-001"
MANIFEST = Path(__file__).resolve().parent / "test_data_manifest.txt"

# Edited in the test copy (see README.md); never overwritten from the live project.
LAYER_FILES = "GIS/3_Mapping/31_Resources/312_Layer_files/3121_arcpro/"
LOCAL_CHANGES = {
    "event_description.json",                         # switched to English
    LAYER_FILES + "admn_adx_py_all_reference.lyrx",   # Bird / Navassa Island labels hidden
    LAYER_FILES + "admn_adx_py_all_location.lyrx",    # Bird / Navassa Island labels hidden
    LAYER_FILES + "admn_ad1_py_all_reference.lyrx",   # standard CMF label (name + pcode)
    "GIS/3_Mapping/32_Map_Templates/321_arcpro/arcpro_templates_automation_test.aprx",  # tidied by tools/clean_template.py
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("live", nargs="?", type=Path, default=DEFAULT_LIVE)
    parser.add_argument("--refresh", action="store_true",
                        help="also replace files that differ from the live project")
    args = parser.parse_args()
    if not args.live.is_dir():
        raise SystemExit(f"Live project not found: {args.live}")

    copied = kept = 0
    missing = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        source, target = args.live / line, TEST_PROJECT / line
        if not source.is_file():
            missing.append(line)
            continue
        if target.is_file():
            unchanged = target.stat().st_size == source.stat().st_size
            if not args.refresh or unchanged or line in LOCAL_CHANGES:
                kept += 1
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    print(f"Copied {copied}, kept {kept}.")
    if missing:
        print("Not found in the live project:")
        for line in missing:
            print("  -", line)


if __name__ == "__main__":
    main()
