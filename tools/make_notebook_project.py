"""Make map_automation_pro.aprx: the empty ArcGIS Pro project that users open
before the notebook.

ArcGIS Pro runs a notebook in the open project's home folder (the folder of
its .aprx), not the notebook's own folder. Opening this project, which sits
next to the notebook in GIS/7_Python/71_Jupyter/map_automation, makes that
folder the working folder, so the notebook finds map_automation_pro_lib.py
and the project it is in.

The project is made from the test copy's (tidied) map template, with its
maps and layouts removed and its clutter tidied the same way as each map
project. Its paths are relative, as seen from
GIS/7_Python/71_Jupyter/map_automation, so the file works in any CMF:
- default geodatabase and toolbox: GIS/6_Pro_Default_Files,
- home folder: not stored, so ArcGIS Pro uses the .aprx's own folder.

It is built in the test copy's map_automation folder (so the relative paths
are right) and then moved to the repository root, next to the notebook.
Symlink it into each example project like the other script files (see
cmf_examples/README.txt). Close it in ArcGIS Pro first.

Usage (ArcGIS Pro's Python, since it uses arcpy and map_automation_pro_lib.py):
    propy.bat tools/make_notebook_project.py [PROJECT_FOLDER]
"""

import argparse
import gc
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import arcpy  # noqa: E402
import map_automation_pro_lib as automation  # noqa: E402
from map_automation_pro_lib import cfg  # noqa: E402

NAME = "map_automation_pro.aprx"
NOTEBOOK_FOLDER = "GIS/7_Python/71_Jupyter/map_automation"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("project", nargs="?", type=Path, default=REPO / "cmf_examples/2026-ven-001")
    args = parser.parse_args()

    root = args.project.absolute()
    if not (root / automation.TEST_MARKER).is_file():
        raise SystemExit(f"{root} has no {automation.TEST_MARKER}, so it may be a live project. Stopping.")
    paths = automation.ProjectPaths.from_root(root)
    template = paths.templates / cfg.TEMPLATE_FILE
    folder = root / NOTEBOOK_FOLDER
    built = folder / "map_automation_pro_new.aprx"
    final = REPO / NAME

    arcpy.mp.ArcGISProject(str(template)).saveACopy(str(built))
    aprx = arcpy.mp.ArcGISProject(str(built))
    view = None
    for view in aprx.listLayouts() + aprx.listMaps():
        aprx.deleteItem(view)
    for setting, path in (("defaultGeodatabase", paths.default_geodatabase()),
                          ("defaultToolbox", paths.default_toolbox())):
        if path.exists():
            setattr(aprx, setting, str(path))
    aprx.save()
    del view, aprx
    gc.collect()  # releases arcpy's hold on the file

    def edit(project):
        automation.clean_project_items(project, folder, root / "GIS")
        automation.set_default_items(project, folder, paths)
        project.pop("homeFolder", None)  # ArcGIS Pro then uses the .aprx's own folder
        project["views"] = []            # nothing to open
        project.pop("viewLayoutXML", None)
        return [(i.get("itemType"), i.get("catalogPath")) for i in project["projectItems"]]

    items = automation.edit_project_json(built, edit)
    os.replace(built, final)
    print(f"{final}: {len(items)} project items")
    for kind, path in items:
        print(f"  {kind:18} {path}")


if __name__ == "__main__":
    main()
