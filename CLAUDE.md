# CLAUDE.md

Development repo for MapAction's ArcGIS Pro map automation script. Read
README.md first for the user-facing picture.

## Key facts

- **Script:** `map_automation_pro.py` and `map_automation_pro_config.py`, at the
  repo root. Each example project links to them with **symlinks** in
  `cmf_examples/<project>/GIS/7_Python/71_Jupyter/map_automation/`. Edit the
  root files only.
- **Constraint:** standard library + ArcGIS Pro's `arcgispro-py3` env only
  (an organisational rule). No pip/conda packages in the script.
- **Planned:** a Jupyter version, to live in the `71_Jupyter/map_automation/`
  folder. Keep logic in functions so a notebook can reuse them.
- **Symlinks on Windows:** Developer Mode is on, and `core.symlinks=true` is set
  for this repo. Create links with `cmd /c mklink`; PowerShell 5.1's
  `New-Item -ItemType SymbolicLink` still demands admin.

## The live project: never touch it

`C:\Users\hmatc\Nextcloud\Projects\2026\2026-ven-001` is the live Venezuela
project, synced to other people via Nextcloud. **Read only. Never write,
edit, run the script against, or open its `.aprx` files with arcpy** (that can
leave lock files). To read inside a live `.aprx`/`.pagx`, open it as a zip or
JSON file instead.

`cmf_examples/2026-ven-001` is a cut-down copy with the same structure.
`GIS/2_Active_Data` is git-ignored; fill it with
`python tools/copy_test_data.py` (reads the files in
`tools/test_data_manifest.txt` from live). Files deliberately edited in the
test copy are listed in README.md and in `LOCAL_CHANGES` in the tool, and are
never overwritten. If the script starts using a new file, add it to the
manifest.

## Running and testing

The script asks three questions on stdin. For the standard test, pipe in the
answers (UTM 19N, location map = same, layout 3 = `landscape_a3_marginalia_inside`):

```
Set-Location cmf_examples\2026-ven-001\GIS\7_Python\71_Jupyter\map_automation
"2", "19N", "0", "3" | & "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" map_automation_pro.py
```

- PowerShell piping adds a BOM; `ask()` strips it. Piping from Git Bash into
  `propy.bat` has quoting problems, so use PowerShell.
- The project is found by walking up from the script's **unresolved** path
  (`Path(__file__).absolute()`, never `.resolve()`), so it must be run via
  the symlink, or with `--project <folder>`.
- arcpy needs ArcGIS Pro signed in. "The Product License has not been
  initialized" means the user must sign in to Pro; ask them.
- MA901 takes about 25 seconds. `TEST_MODE` deletes MA* outputs first, so each
  run gives `v01`. View the JPEG in
  `GIS/3_Mapping/34_Map_Products_MapAction/MA901/v01/` to check the result.
- To inspect a built `.aprx` (broken links, definition queries, labels,
  element text), use `arcpy.mp.ArcGISProject` in a throwaway script outside
  the repo.
- Testing mode refuses to run without `TEST_ENVIRONMENT.txt` in the project
  root. Never create that file in a live project.

## How the script works

- **Project root:** the first folder above the script (or `--project`) that
  holds both `event_description.json` and `GIS/`. (`GIS/` itself holds a blank
  `event_description.json`, which is skipped.)
- **Folders:** from `cmf_description.json`, plus the `3121_arcpro` /
  `321_arcpro` subfolders from the config.
- **Event details:** from `event_description.json`; `language_iso2` is
  upper-cased for `ADM0_EN`-style fields. The country name comes from the
  admin 0 data's `ADM0_<LANG>` field unless `COUNTRY_NAME` is set.
- **Order of a run:** check the config; resolve the datasets (which may ask
  questions); ask the projections and the layout (the layout question shows
  the country's width/height ratio in the Main map projection); clear the old
  outputs in test mode; then build each map.
- **Building a map:**
  1. `saveACopy` the template.
  2. Delete its maps and layouts, then `importDocument(pagx)`. The `.pagx`
     brings its own "Main map" and "Location map".
  3. Add the layers and link them to the data. Save and reopen (label classes
     only see the new data's fields after a reopen).
  4. Set the projections, label language and country definition queries.
  5. Zoom the frames, then fill the legend.
  6. CIM styling: white backgrounds on the legend and on every
     `CIMParagraphTextGraphic`; legend items hide layer names and headings.
  7. Fill in the text elements, then export.
- **Layer names** are set to the config keys (e.g. `admn_ad1_ln_all_reference`)
  so they can be found again. That's why the legend hides layer names and
  shows only the symbol labels.
- **Data matching:** `<prefix><pattern>` is globbed in `2_Active_Data/<folder>`.
  If several files match, `PREFERRED_DATASETS` is checked first, then
  `PREFERRED_SUPPLIER`, then the user is asked.
- **Data naming:**
  `geoext_category_theme_geom_scale_source_permission_free`. The source is
  the part before the permission code (the scale part is sometimes missing).
  `SOURCE_NAMES` maps source codes to the names shown on the map.

## Known gaps / open questions

- MA002 to MA004 are configured but untested by request.
- The `PREFERRED_DATASETS` choices were picked by Claude for testing; confirm
  them with the user.
- The 50% opacity of the `carto_fea_py_all` mask was Claude's choice.
- Venezuela's admin 1 and 2 data has no `_EN` name fields.
- The `.pagx` files (June) may differ from the same-named layouts inside the
  template `.aprx` (October). The script uses the `.pagx`.
