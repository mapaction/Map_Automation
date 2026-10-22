"""Run the map automation notebook's code cells from the command line, for
testing: the answers to its questions can then be piped in.

Run it with ArcGIS Pro's Python from the folder holding the notebook link,
as the notebook would be run inside ArcGIS Pro, e.g. (PowerShell):

    Set-Location cmf_examples\\2026-ven-001\\GIS\\7_Python\\71_Jupyter\\map_automation
    "2", "19N", "0", "3", "ES" | & "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\Scripts\\propy.bat" ..\\..\\..\\..\\..\\..\\tools\\run_notebook.py

The notebook is map_automation_pro.ipynb in the current folder, or the path
given as the first argument.
"""

import json
import sys
from pathlib import Path


def main():
    notebook = Path(sys.argv[1] if len(sys.argv) > 1 else "map_automation_pro.ipynb")
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    # In Jupyter the notebook's folder (the working directory) is on the
    # import path; when run as a script, this file's folder is instead.
    sys.path[0] = str(Path.cwd())
    namespace = {"__name__": "__main__"}
    for number, cell in enumerate(cells):
        if cell["cell_type"] == "code":
            source = "".join(cell["source"])
            exec(compile(source, f"{notebook.name} cell {number}", "exec"), namespace)


if __name__ == "__main__":
    main()
