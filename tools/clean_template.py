"""Tidy a CMF's map template project (.aprx) once, the same way the map
automation script tidies each project it makes:

- removes tool and notebook history, connections to files that don't exist,
  and duplicate connections;
- moves paths into another project's GIS folder (e.g. the project the
  template was made in) to this CMF where the file exists;
- points the default geodatabase and toolbox at GIS/6_Pro_Default_Files.

It only edits the template's GISProject.json; the maps and layouts are not
touched. Like testing mode, it only runs in a project with a
TEST_ENVIRONMENT.txt file. Close the template in ArcGIS Pro first.

Usage (ArcGIS Pro's Python, since it reuses the script's functions):
    propy.bat tools/clean_template.py [PROJECT_FOLDER]
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import map_automation_pro as automation  # noqa: E402
from map_automation_pro import cfg  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", nargs="?", type=Path, default=REPO / "cmf_examples/2026-ven-001")
    args = parser.parse_args()

    root = args.project.absolute()
    if not (root / automation.TEST_MARKER).is_file():
        raise SystemExit(f"{root} has no {automation.TEST_MARKER}, so it may be a live project. Stopping.")
    paths = automation.ProjectPaths.from_root(root)
    template = paths.templates / cfg.TEMPLATE_FILE

    def edit(project):
        before = len(project["projectItems"])
        removed = automation.clean_project_items(project, template.parent, root / "GIS")
        automation.set_default_items(project, template.parent, paths)
        return before, removed, len(project["projectItems"])

    before, removed, after = automation.edit_project_json(template, edit)
    print(f"{template.name}: {before} project items, {removed} removed, {after} now "
          "(including the default geodatabase and toolbox).")


if __name__ == "__main__":
    main()
