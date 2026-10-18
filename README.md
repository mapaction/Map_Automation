# MapAction map automation for ArcGIS Pro

A Python script that builds MapAction map products automatically. For each
map it:

1. copies a template ArcGIS Pro project (`.aprx`),
2. adds the layers for that map (styled by `.lyrx` layer files) and links each
   one to the right dataset in `2_Active_Data`,
3. sets label languages and zooms the main and location maps,
4. fills in the title, summary, map number, GLIDE number, time zone, data
   sources, disclaimer and donor credit,
5. saves the project and exports a JPEG.

This folder is where the script is being developed and tested. It is a
replacement for the Jupyter notebook
`MapAction_Map_Automation_ArcPro_v29.ipynb` (kept for reference, see below).
A notebook version for users who prefer running it inside ArcGIS Pro will be
made later.

## What is in this folder

```
README.md, CLAUDE.md          this guide, and notes for Claude Code sessions
tools/                        rebuilds the test data from the live project
cmf_examples/2026-ven-001/    test copy of the Venezuela project (see below)
  event_description.json      event details used by the script
  cmf_description.json        where the standard folders are
  TEST_ENVIRONMENT.txt        marks this as a test copy (allows testing mode)
  GIS/7_Python/72_Scripts/721_Automation/
    map_automation_pro.py         the script
    map_automation_pro_config.py  settings: which maps, layers, testing mode
  GIS/7_Python/71_Jupyter/
    MapAction_Map_Automation_ArcPro_v29.ipynb   the original notebook
```

## The test environment and the live Venezuela project

MapAction projects all share a fixed folder structure, and the script relies
on it. To test safely, `cmf_examples/2026-ven-001` is a **cut-down copy** of
the live Venezuela project (`Nextcloud/Projects/2026/2026-ven-001`) with the
same folder structure. It holds only the files the script uses, about 400 MB
out of several tens of GB:

- the template project and the layer files the maps use,
- the datasets those layers point to (admin boundaries, settlements,
  transport, elevation, rivers and lakes, world boundaries),
- `event_description.json` and `cmf_description.json` from the project root.

The live project is synced to other users through Nextcloud. **Never edit it
from here, and never run the script in testing mode against it.** All
development and test runs happen in the copy.

The GIS data (`GIS/2_Active_Data`) is too large for git and is not stored in
the repository. To get it, or to refresh it after the live data changes, run:

```
python tools/copy_test_data.py
```

This only reads from the live project. The list of files is in
`tools/test_data_manifest.txt`. If the script needs another dataset, add it to
that list and run the tool again.

## Running the script

Use ArcGIS Pro's Python (ArcGIS Pro must be installed and signed in). From a
command prompt:

```
"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" cmf_examples\2026-ven-001\GIS\7_Python\72_Scripts\721_Automation\map_automation_pro.py
```

Outputs appear in:

- `GIS/3_Mapping/33_Map_Projects/<map code>/` (the `.aprx` projects)
- `GIS/3_Mapping/34_Map_Products_MapAction/<map code>/<version>/` (the JPEGs)

The script works out the project folder from where it is saved, so the same
script works in any project with the standard structure. It reads the event
details from that project's `event_description.json`.

Only the Python standard library and ArcGIS Pro's own `arcpy` are used, so
nothing needs installing.

## Settings

Everything you are likely to change is in `map_automation_pro_config.py`:

| Setting | What it does |
|---|---|
| `TEST_MODE` | `True` deletes all previous outputs of the script before each run. Only works where `TEST_ENVIRONMENT.txt` exists. Set to `False` for real use. |
| `MAPS_TO_RUN` | Map codes to build, e.g. `["MA901"]`. `None` builds all. |
| `TEMPLATE_FILE`, `LAYOUT_NAME` | Template project and the layout used from it. |
| `PREFERRED_SUPPLIER` | When several datasets match a layer, prefer this source (e.g. `ine`). |
| `PREFERRED_DATASETS` | Fixed dataset choice for layers that match several files. Anything still unclear is asked at the start of the run. |
| `COUNTRY_NAME` | Country name on the map. `None` reads it from the admin 0 data, in the event language. |
| `LAYERS` | Every layer that can be used: its layer file, data file pattern, data folder and map frame. |
| `MAPS` | The map products: code, title, summary and which layers they show. |

Event details (GLIDE number, time zone, language, contact email, disclaimer,
donor credit, JPEG resolution) come from `event_description.json`, not from
the config.

## Current state

- **MA901** is the map being tested. It builds cleanly from the test data.
- MA002, MA003 and MA004 are defined but not tested yet.
- There are no legend images for the `portrait_a3_marginalia_inside` layout,
  so the script reports them as missing. The template's own legend is used.

## Changes from the v29 notebook

- Plain Python script with a separate settings file.
- Project folder found automatically. Paths handled with `pathlib`.
- Event details read from `event_description.json` instead of being typed
  into the notebook. The JPEG resolution now follows the event setting
  (300 dpi; it was 200).
- Disclaimer and donor credit are filled in from the event details.
- Testing mode, with a safety check.
- Ambiguous datasets are set in the config rather than always being asked.
- Fixed data patterns that never matched: world boundaries (`adx`),
  Natural Earth rivers and roads. These layers now appear on the map.
- The filter that hides the affected country on the neighbouring-country
  layers now uses `ISO3CD`, which both world boundary datasets have.
- The data source list no longer shows `pp` for files without a scale part.
- Removed the unused ratio-based template selection and the ArcMap notes.
