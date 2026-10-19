# MapAction map automation for ArcGIS Pro

A Python script that builds MapAction map products automatically. For each
map it:

1. creates an ArcGIS Pro project (`.aprx`) from a template and the chosen
   layout (`.pagx`),
2. adds the layers for that map (styled by `.lyrx` layer files) and links each
   one to the right dataset in `2_Active_Data`,
3. sets the projections, label language, and zoom of the Main and Location
   maps,
4. fills in the legend and the title, map number, GLIDE number, data sources,
   disclaimer and other text, with white backgrounds behind the legend and
   text boxes,
5. saves the project and exports a JPEG.

This repository is where the script is developed and tested. It replaces the
Jupyter notebook `MapAction_Map_Automation_ArcPro_v29.ipynb`. A notebook
version, for users who prefer running it inside ArcGIS Pro, will be made later.

## What is in this repository

```
map_automation_pro.py          the script
map_automation_pro_config.py   settings: which maps, layers, testing mode...
README.md, CLAUDE.md           this guide, and notes for Claude Code sessions
tools/                         fills in the test data from the live project
cmf_examples/2026-ven-001/     test copy of the Venezuela project (see below)
  event_description.json       event details used by the script
  cmf_description.json         where the standard folders are
  TEST_ENVIRONMENT.txt         marks this as a test copy (allows testing mode)
  GIS/7_Python/71_Jupyter/map_automation/
                               links (symlinks) to the two script files
```

The real script files are at the top of the repository, so the same script can
be tested against other example projects in `cmf_examples` later. Each
example project gets links to them in `GIS/7_Python/71_Jupyter/map_automation/`,
where a notebook version will eventually live.

Git stores the links as symlinks. On Windows, creating symlinks needs
**Developer Mode** (Settings › System › For developers) and
`git config core.symlinks true` (already set in this repository).

## The test environment and the live Venezuela project

MapAction projects all share a fixed folder structure (the "CMF"), and the
script relies on it. To test safely, `cmf_examples/2026-ven-001` is a
**cut-down copy** of the live Venezuela project
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
| `312_Layer_files/3121_arcpro/carto_fea_py_all.lyrx` | Drawn as a 50% white mask (see below). |

**Bird and Navassa Island labels.** The labels are hidden with
`ROMNAM NOT IN ('Bird Island', 'Navassa Island')`. The ISO code alone can't
be used: Bird Island's code is `VEN`, which would also hide the "Venezuela"
label, and Navassa's is `UMI`, which it shares with other US islands.

**`carto_fea_py_all`.** The layer file was made for "feather" data: several
rings around a country, each with an `xpar` transparency field. The
Venezuelan dataset (`ven_carto_fea_py_mapaction_pp_faded_nationalboundary`)
is different: a single world-wide polygon with the country cut out, and no
`xpar` field. So it drew as solid white. The layer file now draws it as a
semi-transparent white mask, which fades everything outside the country.

## Running the script

Use ArcGIS Pro's Python (ArcGIS Pro must be installed and signed in). Run it
through the link inside the project, so it knows which project to use:

```
cd cmf_examples\2026-ven-001\GIS\7_Python\71_Jupyter\map_automation
"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" map_automation_pro.py
```

or run the real file and name the project:

```
"C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\propy.bat" map_automation_pro.py --project cmf_examples\2026-ven-001
```

At the start it asks three questions:

1. **Main map projection:** ArcGIS Pro default (latitude/longitude, WGS
   1984), a UTM zone (e.g. `19N`; the project's Data Scramble Sheet lists
   it), or an EPSG/ESRI code.
2. **Location map projection:** the same options, plus `0` for "same as the
   Main map".
3. **Layout:** one of the `.pagx` files in
   `GIS/3_Mapping/32_Map_Templates/321_arcpro`. For initial maps, choose a
   layout matching the country's shape; the script says how wide the country
   is compared with its height.

For the Venezuela test: UTM `19N`, `0` (same as Main map),
`landscape_a3_marginalia_inside`.

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
| `MAIN_MAP_PROJECTION`, `LOCATION_MAP_PROJECTION`, `LAYOUT` | Answers to the start-up questions. `None` asks; e.g. `"UTM 19N"`, `"SAME"`, `"landscape_a3_marginalia_inside"` skip the question. |
| `TEMPLATE_FILE` | Base project each map starts from. |
| `PREFERRED_SUPPLIER`, `PREFERRED_DATASETS` | Which dataset to use when several match a layer. Anything still unclear is asked. |
| `COUNTRY_NAME` | Country name on the map. `None` reads it from the admin 0 data, in the event language. |
| `SOURCE_NAMES` | How data sources are written on the map (`naturalearth` → `Natural Earth`). |
| `LEGEND_EXCLUDE` | Main map layers left out of the legend. |
| `LAYERS`, `MAPS` | Every layer that can be used, and the map products made from them. |

Event details (GLIDE number, time zone, language, contact email, disclaimer,
donor credit, JPEG resolution) come from the project's
`event_description.json`, not from the config.

## Current state

- **MA901** builds cleanly from the test data.
- MA002, MA003 and MA004 are defined but not tested yet.
- Venezuela's admin 1 and 2 data only has Spanish names (`ADM1_ES`). The
  script only switches label fields to the event language where the data has
  them, so these labels are not affected. They currently show P-codes.
