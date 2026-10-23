# CLAUDE.md

Development repo for MapAction's ArcGIS Pro map automation notebook. Read
README.md first for the user-facing picture.

## Key facts

- **Files:** at the repo root. Each example project links to them with
  **symlinks** in `cmf_examples/<project>/GIS/7_Python/71_Jupyter/map_automation/`
  (except `map_automation_pro.aprx`, which is copied; see below).
  Edit the root files only.
  - `map_automation_pro.ipynb`: what users run, in ArcGIS Pro. Aimed at
    non-Python users: a markdown cell before each code cell, and each code
    cell is one call to a run step. Keep it that short; logic goes in the lib.
  - `map_automation_pro_lib.py`: all the functions. The run steps the
    notebook calls are at the end (`start_run`, `find_data`, `ask_questions`,
    `check_before_building`, `clear_old_outputs`, `build_maps`).
  - `map_automation_pro_config.py`: settings.
  - The notebook is committed with no outputs. If it was run in Pro, clear
    them before committing (Pro saves outputs into the file via the symlink).
  - `map_automation_pro.aprx`: an empty Pro project that users open before
    the notebook. In Pro, a notebook's working directory is the user's
    home folder (`C:\Users\hmatc`), and it isn't on `sys.path`. So the first
    cell puts `arcpy.mp.ArcGISProject("CURRENT").homeFolder` (this
    project's folder, i.e. the notebook's) on `sys.path`; outside Pro,
    `"CURRENT"` raises `OSError` and it uses the working directory. Made by `tools/make_notebook_project.py` (run with
    `propy.bat`) from the test copy's template; paths relative to
    `GIS/7_Python/71_Jupyter/map_automation`, no stored `homeFolder`.
    Rebuild it rather than editing it; the tool writes both the repo root's
    copy and the test copy's. **The test copy's is a real file, not a
    symlink:** ArcGIS Pro (unlike arcpy) follows the link and resolves the
    relative paths and home folder from the repo root. With a link, Pro
    created `C:\Users\hmatc\6_Pro_Default_Files` and a
    `RasterFunctionTemplates` folder in the repo root.
  - `cmf_examples/`: example projects, downloaded from Google Drive and not
    tracked by git (see "The test copy").
- **Constraint:** standard library + ArcGIS Pro's `arcgispro-py3` env only
  (an organisational rule). No pip/conda packages in the script. If a task
  has an easier solution outside this (e.g. geopandas), **ask the user
  first** rather than using it.
- **Symlinks on Windows:** Developer Mode is on. Create links with
  `cmd /c mklink`; PowerShell 5.1's `New-Item -ItemType SymbolicLink` still
  demands admin. The links are not in git (see "The test copy"); the
  commands are in `cmf_examples/README.txt`.

## The three folders

A **Crash Move Folder (CMF)** is MapAction's standard folder structure for one
disaster response (e.g. `2026-ven-001`). Three related folders are involved:

| Folder | Role | Rule |
|---|---|---|
| `C:\Users\hmatc\Documents\repos\Map_Automation` (this repo) | Where the script is developed and tested, against cut-down CMF copies in `cmf_examples/`. | Work here. |
| `C:\Users\hmatc\Nextcloud\Projects\2026\2026-ven-001` | The **live** CMF for the Venezuela response, synced to MapAction colleagues via Nextcloud. Source of the test copy's files. | **Read only.** |
| `C:\Users\hmatc\Documents\repos\default-crash-move-folder` | The **standard CMF** (git repo `mapaction/default-crash-move-folder`), the starting point for every new response. Its template project folder is `20YYiso3nn/`. | Don't touch during development. |

**Release route:** when the user is happy with the script, it is copied by
hand from this repo into the standard CMF (repo 3), so future responses start
with it. This is a deliberate plain copy, not a git submodule or similar. The
copy must be real files, not symlinks. Only do this when the user asks. Repo 3
already holds older automation material (e.g.
`20YYiso3nn/GIS/7_Python/71_Jupyter/Map_Automation.ipynb` and
`GIS/3_Mapping/31_Resources/318_Python_scripts/map_automation_*.py`); ask the
user what replaces what before copying.

Because the script will run inside the standard CMF structure, it must keep
relying only on that structure (`cmf_description.json`,
`event_description.json`, the standard folder names), never on anything
specific to this repo or to Venezuela.

### The live project: never touch it

`C:\Users\hmatc\Nextcloud\Projects\2026\2026-ven-001` is synced to other
people. **Never write, edit, run the script against, or open its `.aprx`
files with arcpy** (that can leave lock files). To read inside a live
`.aprx`/`.pagx`, open it as a zip or JSON file instead.

### The test copy

`cmf_examples/2026-ven-001` is a cut-down copy with the same structure.
**Nothing in `cmf_examples/` is tracked by git** except
`cmf_examples/README.txt` (the Google Drive download links and setup
steps). The example projects are zipped and kept on Google Drive; locally,
the folder is unzipped there and the symlinks are made by hand.

- `python tools/copy_test_data.py` updates the test copy from live (reads the
  files in `tools/test_data_manifest.txt`). Files deliberately edited in
  the test copy are listed in README.md and in `LOCAL_CHANGES` in the tool,
  and are never overwritten. If the script starts using a new file, add it
  to the manifest.
- After changing an example, `python tools/zip_example.py 2026-ven-001`
  writes `../2026-ven-001.zip` (no symlinks, outputs or clutter) for the
  user to upload to Drive. Don't upload it yourself. If the link changes,
  update `cmf_examples/README.txt`.
- Since the examples aren't in git, changes to them (e.g. a `LOCAL_CHANGES`
  file) don't show in `git status` or diffs. Mention them to the user so
  the Drive copy gets updated.

## Running and testing

`tools/run_notebook.py` runs the notebook's code cells in order as a plain
script, so the questions (projections, layout, admin label language) can be
answered on stdin. For the standard test, pipe in the answers (UTM 19N,
location map = same, layout 3 = `landscape_a3_marginalia_inside`, admin
labels from `ADM1_ES` / `ADM2_ES`):

```
Set-Location cmf_examples\2026-ven-001\GIS\7_Python\71_Jupyter\map_automation
"2", "19N", "0", "3", "ES" | & "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" ..\..\..\..\..\..\tools\run_notebook.py
```

- PowerShell piping adds a BOM; `ask()` strips it. Piping from Git Bash into
  `propy.bat` has quoting problems, so use PowerShell.
- The project is found by walking up from the working directory (in
  Pro, the user's home folder, so this finds nothing), then from the lib's
  **unresolved** path (`Path(__file__).absolute()`, never `.resolve()`; in
  Pro, `map_automation_pro.aprx`'s folder, see above). So run from the symlink
  folder, or set `PROJECT_FOLDER` in the notebook's first code cell.
- arcpy needs ArcGIS Pro signed in. "The Product License has not been
  initialized" means the user must sign in to Pro; ask them.
- MA901 takes about 35 seconds. `TEST_MODE` deletes MA* outputs first, so each
  run gives `v01`. View the JPEG in
  `GIS/3_Mapping/34_Map_Products_MapAction/MA901/v01/` to check the result.
- To inspect a built `.aprx` (broken links, definition queries, labels,
  element text), use `arcpy.mp.ArcGISProject` in a throwaway script outside
  the repo.
- Testing mode refuses to run without `TEST_ENVIRONMENT.txt` in the project
  root. Never create that file in a live project.

## How the script works

- **Project root:** the first folder above the working directory (or the
  lib, or `PROJECT_FOLDER`) that holds both `event_description.json` and `GIS/`. (`GIS/` itself holds a blank
  `event_description.json`, which is skipped.)
- **Folders:** from `cmf_description.json`, plus the `3121_arcpro` /
  `321_arcpro` subfolders from the config.
- **Event details:** from `event_description.json`; `language_iso2` is
  upper-cased for `ADM0_EN`-style fields. The country name comes from the
  admin 0 data's `ADM0_<LANG>` field unless `COUNTRY_NAME` is set.
- **Order of a run:** check the config; resolve the datasets (which may ask
  questions) and make the feather; ask the projections, the layout (the
  question shows the country's width/height ratio in the Main map projection)
  and the admin label language; clear the old outputs in test mode (stops
  with a message if a file is open in Pro); then build each map. Each of
  these is one notebook cell (one run-step function in the lib).
- **Building a map:**
  1. `saveACopy` the template, then at once set its home folder (the
     project's own folder) and its default geodatabase and toolbox (the
     standard CMF's empty `GIS/6_Pro_Default_Files/MapActionDefault.gdb` and
     `Default.tbx`). The template's own paths point at the project it was
     made in, so Pro asked for them on every open, and arcpy once created a
     stray `cmf_examples/2025/2025-mmr-001/` folder for them (deleted). If
     that folder reappears, something is using the template's old paths
     again.
  2. Delete its maps and layouts, then `importDocument(pagx)`. The `.pagx`
     brings its own "Main map" and "Location map".
  3. Add the layers and link them to the data. Save and reopen (label classes
     only see the new data's fields after a reopen).
  4. Set the projections, label language (`ADM0_xx` from the event
     language, `ADM1_xx`/`ADM2_xx` from the admin label question; a field is
     only switched if the data has it), definition queries
     (`exclude_affected_country` on `ISO3CD`, `only_affected_country` on a
     lower-case ISO3 field) and `labels=False`.
  5. `zoom_frames`: fit each frame to its `FRAME_EXTENTS` layer, multiply,
     then `round_scale_up` (step about scale x `SCALE_ROUNDING_FRACTION`,
     from the 1-2-5 series; always rounds up). `fit_scale_bar`: one division
     of the smallest d x 10^n km at least `SCALE_BAR_MIN_WIDTH` of the page
     wide, `AdjustFrame`, anchor position restored (keeps the layout's
     alignment), text x `SCALE_BAR_TEXT_SIZE_FACTOR`. Then fill the legend,
     setting `LEGEND_HEADINGS` on the layers (raster colorizer or renderer
     heading).
  6. CIM styling: white backgrounds on the legend and on every
     `CIMParagraphTextGraphic`, except text in `GROUP_BACKGROUNDS` groups,
     which share one background on the group's own frame (75% opaque);
     legend columns from the page shape; legend items hide layer names, and
     headings unless in `LEGEND_HEADINGS`.
  7. Fill in the text elements, then export.
  8. After the project is closed, `finish_project_file` edits its
     `GISProject.json` (the `.aprx` is a zip): `clean_project_items` drops
     tool/notebook history, broken and duplicate connections, and moves
     paths into another project's `GIS` folder to this one; then
     `open_views_on_start` makes Pro open the Main map, Location map and
     layout as tabs, the maps at their frames' centre and scale. arcpy's
     `openView` only works inside a running Pro, hence the direct edit. If
     Pro ever rejects a project, suspect this step first.
- **Template:** the test copy's template was tidied once with
  `tools/clean_template.py` (same functions; run with `propy.bat`), so it is
  a `LOCAL_CHANGES` file. The standard CMF's template is untouched; the
  script tidies whatever template it is given.
- **Layer names** are set to the config keys (e.g. `admn_ad1_ln_all_reference`)
  so they can be found again. That's why the legend hides layer names and
  shows only the symbol labels.
- **Drawing order** is each `MapSpec.layers` list, top first (layers are
  added at the bottom in turn). The feather is first, so it fades
  everything outside the country; labels always draw above it.
- **Data matching:** `<prefix><pattern>` is globbed in `2_Active_Data/<folder>`.
  If several files match, `PREFERRED_DATASETS` is checked first, then
  `PREFERRED_SUPPLIER`, then the user is asked.
- **Feather (`carto_fea_py_all`):** not globbed. `make_feather` erases the
  chosen admin 0 polygon from `FEATHER_BACKGROUND` (the Data Scramble
  toolbox's "2.1 Create Feather" logic) into `207_carto`, and `style_feather`
  replaces the `.lyrx` symbol with stacked offset white fills (the live
  response's symbol). The standard `.lyrx` expects old `xpar` ring data, so
  it is deliberately ignored. See README.md.
- **Data naming:**
  `geoext_category_theme_geom_scale_source_permission_free`. The source is
  the part before the permission code (the scale part is sometimes missing).
  `SOURCE_NAMES` maps source codes to the names shown on the map.

## Known gaps / open questions

- The first run inside ArcGIS Pro (the live Venezuela project, which has a
  plain copy of the script, with `TEST_MODE = False`, in
  `GIS/7_Python/71_Jupyter/map_automation/`) failed with
  `ModuleNotFoundError`, even with `map_automation_pro.aprx` open: the
  kernel's working directory is the user's home folder and isn't on
  `sys.path` (checked in Pro: the project's `homeFolder` was right).
  Loading from `ArcGISProject("CURRENT").homeFolder` is the fix; still to
  confirm in Pro, along with `input()` prompts working. The live copy
  doesn't update itself: after a fix, the user copies the changed files
  across (writes to live need the user's say-so each time).
- At release, the standard CMF also has an older
  `71_Jupyter/blank_template_for_running_Jupyter_automation.aprx` (same
  idea, but cluttered and with Myanmar paths); ask the user whether
  `map_automation_pro.aprx` replaces it.

- MA002 to MA004 are configured but untested by request.
- The `PREFERRED_DATASETS` choices were picked by Claude for testing; confirm
  them with the user.
- The feather is not yet on the Location map (its `LayerSpec` is commented
  out).
- The standard CMF's `carto_fea_py_all.lyrx` still has the old `xpar`
  symbol. The script doesn't need it changed, but the user may want to.
- The opening tabs and project tidying (step 8) are checked with arcpy only;
  the user has yet to confirm the result in ArcGIS Pro.
- The standard CMF's template has the same clutter as the test copy's had.
  The script copes, but `tools/clean_template.py` could be run on it at
  release time (with the user's say-so).
- Venezuela's admin 1 and 2 data has no `_EN` name fields; the test answers
  `ES` to the admin label question. The test copy's
  `admn_ad1_py_all_reference.lyrx` had to be put back to the standard label
  (the live one labels P-codes only); it is a `LOCAL_CHANGES` file.
- Since the scale bar, legend columns and group background were added, only
  `landscape_a3_marginalia_inside` has been run. Portrait layouts (two-column
  legend) and right/centre-anchored scale bars are untested.
- Small admin 1 polygons are labelled as a numbered list placed by Pro
  (from the `.lyrx` label settings); on MA901 it sits partly over Colombia.
- The `.pagx` files (June) may differ from the same-named layouts inside the
  template `.aprx` (October). The script uses the `.pagx`.
