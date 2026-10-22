# MapAction map automation for ArcGIS Pro

A Jupyter notebook, run inside ArcGIS Pro, that builds MapAction map products
automatically. No Python knowledge is needed to run it. For each map it:

1. creates an ArcGIS Pro project (`.aprx`) from a template and the chosen
   layout (`.pagx`), using the CMF's default geodatabase and toolbox,
2. adds the layers for that map (styled by `.lyrx` layer files) and links each
   one to the right dataset in `2_Active_Data`; the feather layer, which
   fades everything outside the country, is made fresh from the country's
   boundary (see below),
3. sets the projections, label language and country filters (e.g. only the
   country's own ports), zooms the Main and Location maps to tidy scales, and
   sizes the scale bar,
4. fills in the legend and the title, map number, GLIDE number, data sources,
   disclaimer and other text, with white backgrounds behind the legend and
   text boxes (one shared, partly transparent background for the
   bottom-right marginalia group),
5. saves the project and exports a JPEG,
6. tidies the project (removes clutter inherited from the template) and sets
   it to open with the Main map, Location map and layout as tabs, the maps at
   the same view as on the layout.

This repository is where it is developed and tested. It replaces the
Jupyter notebook `MapAction_Map_Automation_ArcPro_v29.ipynb`.

## How this repository relates to the Crash Move Folders

Each MapAction disaster response (e.g. `2026-ven-001`) has its own **Crash
Move Folder (CMF)**: a folder with a fixed, standard structure. Three folders
are involved in this work:

1. **This repository** (`Documents/repos/Map_Automation`): where the script
   is developed and tested, against cut-down copies of real CMFs in
   `cmf_examples/`.
2. **The live Venezuela CMF** (`Nextcloud/Projects/2026/2026-ven-001`): used
   by MapAction for the response and synced to colleagues through Nextcloud.
   Many of the test files were copied from it. It is **never edited** from
   here.
3. **The standard CMF** (`Documents/repos/default-crash-move-folder`, the
   `mapaction/default-crash-move-folder` repository): the empty CMF that every
   new response starts from. It is not touched during development.

When the script is ready, it will be copied from this repository into the
standard CMF (3), so every future response has it. This is a plain copy,
not a git link between the repositories. Because of this, the script must
only rely on the standard CMF structure, never on anything specific to this
repository or to Venezuela.

## What is in this repository

```
map_automation_pro.ipynb       the notebook users run, step by step
map_automation_pro_lib.py      the functions behind the notebook
map_automation_pro_config.py   settings: which maps, layers, testing mode...
README.md, CLAUDE.md           this guide, and notes for Claude Code sessions
tools/                         fills in the test data from the live project;
                               tidies the test copy's map template; runs the
                               notebook from the command line for testing
cmf_examples/2026-ven-001/     test copy of the Venezuela project (see below)
  event_description.json       event details used by the script
  cmf_description.json         where the standard folders are
  TEST_ENVIRONMENT.txt         marks this as a test copy (allows testing mode)
  GIS/6_Pro_Default_Files/     empty default geodatabase and toolbox, copied
                               from the standard CMF; every new project uses them
  GIS/7_Python/71_Jupyter/map_automation/
                               links (symlinks) to the three files above
```

The real files are at the top of the repository, so the same notebook can
be tested against other example projects in `cmf_examples` later. Each
example project gets links to them in `GIS/7_Python/71_Jupyter/map_automation/`.

Git stores the links as symlinks. On Windows, creating symlinks needs
**Developer Mode** (Settings › System › For developers) and
`git config core.symlinks true` (already set in this repository).

## The test environment and the live Venezuela project

The script relies on the standard CMF structure. To test safely,
`cmf_examples/2026-ven-001` is a **cut-down copy** of the live Venezuela CMF
(`Nextcloud/Projects/2026/2026-ven-001`) with the same folder structure. It
holds only the files the script uses: about 400 MB out of several tens of
GB.

The live project is synced to other users through Nextcloud. **Never edit it
from here, and never run the script in testing mode against it.** All
development and test runs happen in the copy.

The GIS data (`GIS/2_Active_Data`) is too large for git and is not stored in
the repository. To fill it in, run:

```
python tools/copy_test_data.py            # copy missing files only
python tools/copy_test_data.py --refresh  # also update files changed in the live project
```

This only reads from the live project. The list of files is in
`tools/test_data_manifest.txt`.

### Files deliberately different from the live project

These are edited in the test copy and are never overwritten by the copy tool:

| File | Change |
|---|---|
| `event_description.json` | Language switched to English (`en`); disclaimer and donor credit translated. |
| `312_Layer_files/3121_arcpro/admn_adx_py_all_reference.lyrx`, `admn_adx_py_all_location.lyrx` | Bird Island and Navassa Island are not labelled. |
| `312_Layer_files/3121_arcpro/admn_ad1_py_all_reference.lyrx` | Label expression put back to the standard CMF's `[ADM1_EN] & vbNewLine & [ADM1_PCODE]` (the live copy labels with `[ADM1_PCODE]` only), so the admin label language question can switch it to `ADM1_ES`. |
| `32_Map_Templates/321_arcpro/arcpro_templates_automation_test.aprx` | Tidied with `tools/clean_template.py`: old tool and notebook history and broken connections (to the project the template was made in) removed; default geodatabase and toolbox set to `GIS/6_Pro_Default_Files`. The script also tidies every project it makes, whatever the template. |

**Bird and Navassa Island labels.** The labels are hidden with
`ROMNAM NOT IN ('Bird Island', 'Navassa Island')`. The ISO code alone can't
be used: Bird Island's code is `VEN`, which would also hide the "Venezuela"
label, and Navassa's is `UMI`, which it shares with other US islands.

## The feather (`carto_fea_py_all`)

The feather fades everything outside the affected country. The script makes
its data fresh, in the same way as tool "2.1 Create Feather" in MapAction's
Data Scramble toolbox (`GIS/6_Pro_Default_Files/MapAction_Data_Scramble_2023.atbx`
in the standard CMF): it erases the admin 0 polygon used for the maps from the
global background polygon
(`207_carto/wrl_carto_ext_py_s0_esri_pp_globalBackground.shp`). The result is
saved in `2_Active_Data/207_carto` with the toolbox's file name, e.g.
`ven_carto_fea_py_mapaction_pp_faded_country.shp`. It is reused if it is newer
than both inputs; in testing mode it is always remade.

The script also sets the feather's symbol itself, ignoring the layer file's.
The standard `carto_fea_py_all.lyrx` was made for older feather data (rings
around the country, each with an `xpar` transparency field), so it draws the
toolbox's single polygon as solid white. The script instead uses the symbol
from the Venezuela response's maps: 21 stacked white fills at 15% opacity,
each pulled 5 points further from the border, so the fade builds up gradually
and is almost white about 35 mm from the border. The numbers are
`FEATHER_STEPS`, `FEATHER_STEP_PT` and `FEATHER_STEP_OPACITY` in the config.

## Running the notebook

In ArcGIS Pro (signed in), open
`GIS/7_Python/71_Jupyter/map_automation/map_automation_pro.ipynb` from the
project's Catalog pane. Run its cells from the top, one at a time
(Ctrl+Enter) or with **Run All Cells**. Each step has a short explanation
above it. The notebook finds the project it sits in; to use a different
project, set `PROJECT_FOLDER` in its first code cell.

For testing, the notebook can also be run from the command line, with the
answers to its questions piped in (PowerShell):

```
cd cmf_examples\2026-ven-001\GIS\7_Python\71_Jupyter\map_automation
"2", "19N", "0", "3", "ES" | & "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" ..\..\..\..\..\..\tools\run_notebook.py
```

It asks four questions:

1. **Main map projection:** ArcGIS Pro default (latitude/longitude, WGS
   1984), a UTM zone (e.g. `19N`; the project's Data Scramble Sheet lists
   it), or an EPSG/ESRI code.
2. **Location map projection:** the same options, plus `0` for "same as the
   Main map".
3. **Layout:** one of the `.pagx` files in
   `GIS/3_Mapping/32_Map_Templates/321_arcpro`. For initial maps, choose a
   layout matching the country's shape; the script says how wide the country
   is compared with its height.
4. **Admin label language:** the `xx` in the `ADM1_xx` / `ADM2_xx` name
   fields used in admin 1 and 2 labels (default `EN`). The script lists the
   name fields it found in the data. Admin 0 labels follow the event language.

For the Venezuela test: UTM `19N`, `0` (same as Main map),
`landscape_a3_marginalia_inside`, `ES` (the data only has `ADM1_ES`).

## Map scales, scale bar and legend

- **Scales:** each map frame is zoomed to the country, then its scale is
  multiplied (Location map: x2, to show the region) and **rounded up**, so the
  country is never clipped. The rounding step grows with the scale: about a
  twentieth of it, from the series 1, 2, 5, 10, 20, 50... (e.g. between
  1:100,000 and 1:1,000,000 the step is 5,000, 10,000, 20,000 or 50,000). A
  map is zoomed out by under 8%. The fitted and rounded scales are printed.
- **Scale bar:** one division of the smallest "nice" number of km (1-9,
  10-90, 100-900...) that makes it at least 5% of the page width. It keeps the
  layout's alignment; its text is twice the layout's size and reads `km`.
- **Legend:** one column on landscape layouts, two on portrait. Layer names
  and headings are hidden (layer names are config codes), except for layers
  given a heading in `LEGEND_HEADINGS`, e.g. "Elevation (m)" for the DEM.

Outputs appear in:

- `GIS/3_Mapping/33_Map_Projects/<map code>/` (the `.aprx` projects)
- `GIS/3_Mapping/34_Map_Products_MapAction/<map code>/<version>/` (the JPEGs)

Only the Python standard library and ArcGIS Pro's own `arcpy` are used, so
nothing needs installing.

## Settings

Everything you are likely to change is in `map_automation_pro_config.py`:

| Setting | What it does |
|---|---|
| `TEST_MODE` | `True` deletes all previous outputs of the script before each run. Only works where `TEST_ENVIRONMENT.txt` exists. Set to `False` for real use. |
| `MAPS_TO_RUN` | Map codes to build, e.g. `["MA901"]`. `None` builds all. |
| `MAIN_MAP_PROJECTION`, `LOCATION_MAP_PROJECTION`, `LAYOUT`, `ADMIN_LABEL_LANGUAGE` | Answers to the start-up questions. `None` asks; e.g. `"UTM 19N"`, `"SAME"`, `"landscape_a3_marginalia_inside"`, `"ES"` skip the question. |
| `TEMPLATE_FILE` | Base project each map starts from. |
| `PRO_DEFAULT_FILES_FOLDER`, `DEFAULT_GEODATABASE`, `DEFAULT_TOOLBOX` | Default geodatabase and toolbox of each new project (the empty placeholders in `GIS/6_Pro_Default_Files`). |
| `FEATHER_LAYER`, `FEATHER_BACKGROUND` | The feather layer, and the global background polygon its data is made from. |
| `FEATHER_STEPS`, `FEATHER_STEP_PT`, `FEATHER_STEP_OPACITY` | The feather's fade: how many white fills, how far apart (points), and how opaque each is. |
| `PREFERRED_SUPPLIER`, `PREFERRED_DATASETS` | Which dataset to use when several match a layer. Anything still unclear is asked. |
| `COUNTRY_NAME` | Country name on the map. `None` reads it from the admin 0 data, in the event language. |
| `SOURCE_NAMES` | How data sources are written on the map (`naturalearth` → `Natural Earth`). |
| `FRAME_EXTENTS`, `SCALE_ROUNDING_FRACTION` | The layer each map frame is zoomed to and its scale multiplier; the size of the rounding step. |
| `SCALE_BAR_NAME`, `SCALE_BAR_MIN_WIDTH`, `SCALE_BAR_TEXT_SIZE_FACTOR`, `SCALE_BAR_UNIT_LABEL` | The scale bar: minimum width (fraction of the page), text size and unit label. |
| `LEGEND_EXCLUDE`, `LEGEND_HEADINGS`, `LEGEND_COLUMNS_LANDSCAPE`, `LEGEND_COLUMNS_PORTRAIT` | Main map layers left out of the legend; headings shown for some layers; legend columns. |
| `GROUP_BACKGROUNDS` | Layout groups that share one white background (with its opacity) instead of one per text box. |
| `LAYERS`, `MAPS` | Every layer that can be used, and the map products made from them. A `LayerSpec` can hide the affected country (`exclude_affected_country`), show only it (`only_affected_country`, a field with the lower-case ISO3 code) or turn labels off (`labels=False`). A map's `layers` list is its drawing order, top first; the feather is on top. |

Event details (GLIDE number, time zone, language, contact email, disclaimer,
donor credit, JPEG resolution) come from the project's
`event_description.json`, not from the config.

## Current state

- **MA901** builds cleanly from the test data (about 40 seconds).
- The notebook has been tested from the command line
  (`tools/run_notebook.py`), but not yet run inside ArcGIS Pro.
- The feather, default geodatabase and toolbox, project tidying and opening
  tabs are new; the tabs and tidying are checked with arcpy but not yet
  confirmed by opening the project in ArcGIS Pro.
- The feather is not yet added to the Location map.
- MA002, MA003 and MA004 are defined but not tested yet.
- Only `landscape_a3_marginalia_inside` has been tested since the scale bar,
  legend column and group background changes; the other layouts (including
  portrait, with its two-column legend) have not.
- Venezuela's admin 1 and 2 data only has Spanish names (`ADM1_ES`), so the
  test answers `ES` to the admin label language question.
