# CLAUDE.md

Development repo for MapAction's ArcGIS Pro map automation script. Read
README.md first for the user-facing picture.

## Key facts

- **Script:** `cmf_examples/2026-ven-001/GIS/7_Python/72_Scripts/721_Automation/map_automation_pro.py`
  plus `map_automation_pro_config.py` (all user-editable settings).
- **Reference:** `cmf_examples/2026-ven-001/GIS/7_Python/71_Jupyter/MapAction_Map_Automation_ArcPro_v29.ipynb`
  is the notebook the script was refactored from. Don't edit it.
- **Constraint:** standard library + ArcGIS Pro's `arcgispro-py3` env only
  (an organisational rule). No pip/conda packages in the script.
- **Planned:** a Jupyter version for users who run code inside ArcGIS Pro.
  Keep logic in functions so a notebook can import or reuse them;
  `script_dir()` already falls back to the cwd when `__file__` is missing.

## The live project: never touch it

`C:\Users\hmatc\Nextcloud\Projects\2026\2026-ven-001` is the live Venezuela
project, synced to other people via Nextcloud. **Read only. Never write,
edit, run the script against, or create files in it.**
`cmf_examples/2026-ven-001` is a cut-down copy with the same structure,
holding only what the script uses. `GIS/2_Active_Data` is git-ignored (about
400 MB, and one file is over 100 MB); rebuild it with
`python tools/copy_test_data.py`, which reads the files in
`tools/test_data_manifest.txt` from the live project. If the script starts
using a new file, add it to the manifest and copy it in the same way.

## Running and testing

```
& "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" cmf_examples\2026-ven-001\GIS\7_Python\72_Scripts\721_Automation\map_automation_pro.py
```

- arcpy needs ArcGIS Pro signed in. "The Product License has not been
  initialized" means the user must sign in to Pro; ask them.
- MA901 takes about 12 seconds. `TEST_MODE = True` deletes the MA* output folders
  first, so each run gives `v01`. Check the JPEG in
  `GIS/3_Mapping/34_Map_Products_MapAction/MA901/v01/` by viewing it.
- To inspect a built `.aprx` (broken links, definition queries, label
  expressions, element text), open it with `arcpy.mp.ArcGISProject` in a
  throwaway script outside the repo.
- Testing mode refuses to run unless `TEST_ENVIRONMENT.txt` is in the
  project root. Never create that file in a live project.

## How the script finds things

- **Project root:** walks up from the script folder to the first folder
  holding both `event_description.json` and `GIS/`. (`GIS/` itself holds a
  blank `event_description.json` template, which must be skipped.)
- **Folders:** come from `cmf_description.json`, plus the `3121_arcpro` /
  `321_arcpro` subfolders from the config.
- **Event details:** come from `event_description.json`: ISO3, GLIDE number,
  time zone, `language_iso2` (upper-cased, used for `ADM0_ES` /
  `ADM1_ES` label fields), producer text, disclaimer, donor credit and JPEG
  dpi. The country name is not in that file; it is read from the admin 0
  data's `ADM0_<LANG>` field unless `COUNTRY_NAME` is set.
- **Data matching:** `<prefix><pattern>` is globbed in `2_Active_Data/<folder>`.
  The prefix is the event ISO3, `wrl` (world) or `reg`. If several files
  match, `PREFERRED_DATASETS` is checked first, then `PREFERRED_SUPPLIER`;
  anything left is asked with `input()`, and a non-interactive run skips
  the layer.
- **MapAction data naming:**
  `geoext_category_theme_geom_scale_source_permission_free.ext`. The scale
  part is sometimes missing, so `data_source_of()` takes the part before
  the permission code (`pp`, `hp`...; see the live project's
  `2_Active_Data/200_data_name_lookup/`).
- **Build order:** for each map, add and link the layers, save, close and
  reopen, then set label languages and definition queries, zoom, and fill
  in the text. The reopen is deliberate: label classes don't see the new
  data's fields until then.
- **Copies of the template:** made with `saveACopy`, not a file copy, so
  the copy gets new internal IDs. Read-only flags are cleared on the copy.

## Known gaps / open questions

- No legend JPGs exist for `portrait_a3_marginalia_inside`. The
  `LEGEND_IMAGE_POSITIONS` values are placeholders.
- MA002 to MA004 are configured but untested by request. MA003/MA004 need
  `admn_ad2_*`, `tran_rds_ln_natearth`, and the ad2 data, all of which are in
  the test copy.
- The `PREFERRED_DATASETS` choices were picked by Claude for testing and
  should be confirmed with the user.
- World countries have empty `ADM0_ES` for some features, which may matter if
  the adx label expressions switch to `ADM0_<LANG>`. They currently use `[ROMNAM]`.
