"""MapAction map automation for ArcGIS Pro.

Builds map projects (.aprx) and JPEG exports from a template project, a
layout (.pagx), layer files (.lyrx) and the data in 2_Active_Data, using the
standard MapAction project folder structure.

Run it with ArcGIS Pro's Python, from inside a project folder, e.g.:
    "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\Scripts\\propy.bat" map_automation_pro.py
or point it at a project folder:
    ... map_automation_pro.py --project C:\\path\\to\\2026-ven-001

At the start it asks for the Main map and Location map projections and the
layout (unless they are set in the config). Other settings (which maps to
run, testing mode, layers, map definitions) are in map_automation_pro_config.py,
next to this file. Event details are read from event_description.json at the
root of the project folder.

Only the standard library and arcpy are used.
"""

import argparse
import gc
import json
import math
import os
import re
import shutil
import stat
import sys
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import arcpy


def script_dir():
    """Folder this script was run from. Symlinks are deliberately NOT
    resolved, so a link to the script inside a project folder finds that
    project. Falls back to the working directory when there is no file
    (e.g. code pasted into ArcGIS Pro's Python window)."""
    try:
        return Path(__file__).absolute().parent
    except NameError:
        return Path.cwd()


sys.path.insert(0, str(script_dir()))
import map_automation_pro_config as cfg  # noqa: E402

TEST_MARKER = "TEST_ENVIRONMENT.txt"
MAIN = "Main map"
LOCATION = "Location map"


# =============================================================================
# Project folder and event details
# =============================================================================

def find_project_root(start):
    """Walk up from `start` to the project root: the first folder holding both
    event_description.json and a GIS folder (GIS itself holds a blank copy of
    event_description.json, which is skipped)."""
    for folder in (start, *start.parents):
        if (folder / "event_description.json").is_file() and (folder / "GIS").is_dir():
            return folder
    raise SystemExit(
        f"No project folder (with event_description.json and GIS/) found above {start}.\n"
        "Run the script from inside a project folder, or use --project <folder>.")


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    active_data: Path
    layer_files: Path
    templates: Path
    map_projects: Path
    map_exports: Path
    pro_defaults: Path   # 6_Pro_Default_Files (default geodatabase and toolbox)

    @classmethod
    def from_root(cls, root):
        """Folder locations come from cmf_description.json (standard defaults if it is missing)."""
        cmf = {}
        cmf_file = root / "cmf_description.json"
        if cmf_file.is_file():
            cmf = json.loads(cmf_file.read_text(encoding="utf-8"))

        def folder(key, default):
            return root / cmf.get(key, default)

        return cls(
            root=root,
            active_data=folder("active_data", "GIS/2_Active_Data"),
            layer_files=folder("layer_rendering", "GIS/3_Mapping/31_Resources/312_Layer_files")
            / cfg.LAYER_FILES_SUBFOLDER,
            templates=folder("map_templates", "GIS/3_Mapping/32_Map_Templates") / cfg.TEMPLATES_SUBFOLDER,
            map_projects=folder("map_projects", "GIS/3_Mapping/33_Map_Projects"),
            map_exports=folder("export_dir", "GIS/3_Mapping/34_Map_Products_MapAction"),
            pro_defaults=root / cfg.PRO_DEFAULT_FILES_FOLDER,
        )

    def default_geodatabase(self):
        return self.pro_defaults / cfg.DEFAULT_GEODATABASE

    def default_toolbox(self):
        return self.pro_defaults / cfg.DEFAULT_TOOLBOX

    def data_scramble_sheet_url(self):
        """Link from the '... Data Scramble Sheet.url' shortcut in the project root, if any."""
        for shortcut in self.root.glob("*Data Scramble Sheet*.url"):
            match = re.search(r"^URL=(.+)$", shortcut.read_text(errors="ignore"), re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None


@dataclass(frozen=True)
class Event:
    """The fields of event_description.json that the maps use."""
    operation_id: str
    iso3: str          # lower case, as used in data file names
    glide: str
    time_zone: str
    language: str      # upper case, as used in field names (ADM1_EN)
    producer: str
    disclaimer: str
    donor_credits: str
    jpeg_dpi: int

    @classmethod
    def from_json(cls, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        url = re.sub(r"^https?://", "", data.get("default_source_organisation_url", "")).rstrip("/")
        producer_lines = [
            "Produced by " + data.get("default_source_organisation", "MapAction"),
            url,
            data.get("deployment_primary_email", ""),
        ]
        return cls(
            operation_id=data.get("operation_id", ""),
            iso3=data["affected_country_iso3"].lower(),
            glide=data.get("glide_number", ""),
            time_zone=data.get("time_zone", ""),
            language=data.get("language_iso2", "en").upper(),
            producer="\n".join(line for line in producer_lines if line),
            disclaimer=data.get("default_disclaimer_text", ""),
            donor_credits=data.get("default_donor_credits", ""),
            jpeg_dpi=int(data.get("default_jpeg_res_dpi") or 300),
        )


# =============================================================================
# Asking the user
# =============================================================================

def ask(prompt, config_name):
    """input() that explains what to do when nobody can answer (e.g. a
    scheduled or piped run)."""
    try:
        return input(prompt).strip().lstrip("﻿")  # piped input may start with a BOM
    except EOFError:
        raise SystemExit(f"\nNo answer possible here. Set {config_name} in "
                         "map_automation_pro_config.py to skip this question.")


def choose_number(prompt, lowest, highest, config_name):
    while True:
        answer = ask(prompt, config_name)
        if answer.isdigit() and lowest <= int(answer) <= highest:
            return int(answer)
        print(f"  Please enter a number from {lowest} to {highest}.")


# =============================================================================
# Projections
# =============================================================================

UTM_ZONE = re.compile(r"^(?:UTM)?\s*(\d{1,2})\s*([NS])$", re.IGNORECASE)


def parse_projection(text, main=None):
    """Turn 'WGS84', 'UTM 19N', 'EPSG:32619', 'ESRI:102033', '32619' or
    'SAME' into a SpatialReference. Raises ValueError if it can't."""
    text = text.strip().upper()
    if text == "SAME":
        if main is None:
            raise ValueError("'SAME' only applies to the Location map")
        return main
    if text in ("WGS84", "WGS 84", "DEFAULT"):
        wkid = 4326
    elif match := UTM_ZONE.match(text):
        zone, hemisphere = int(match.group(1)), match.group(2)
        if not 1 <= zone <= 60:
            raise ValueError(f"UTM zones run from 1 to 60, not {zone}")
        wkid = (32600 if hemisphere == "N" else 32700) + zone  # WGS 1984 UTM
    else:
        code = re.sub(r"^(EPSG|ESRI)\s*:\s*", "", text)
        if not code.isdigit():
            raise ValueError(f"'{text}' is not a UTM zone or an EPSG/ESRI code")
        wkid = int(code)
    try:
        return arcpy.SpatialReference(wkid)
    except RuntimeError:
        raise ValueError(f"{wkid} is not a known EPSG/ESRI code")


def ask_projection(frame_name, config_name, scramble_url, main=None):
    print(f"\nProjection for the {frame_name}:")
    if main is not None:
        print(f"  0: same as the Main map ({pretty_name(main)})")
    print("  1: ArcGIS Pro default (latitude/longitude, WGS 1984)")
    hint = f": {scramble_url}" if scramble_url else " in the project folder"
    print(f"  2: UTM zone, e.g. 19N (not sure? check the Data Scramble Sheet{hint})")
    print("  3: EPSG or ESRI code, e.g. 32619")
    while True:
        choice = choose_number(f"Choose {0 if main else 1}-3: ", 0 if main else 1, 3, config_name)
        try:
            if choice == 0:
                return main
            if choice == 1:
                return parse_projection("WGS84")
            if choice == 2:
                return parse_projection("UTM " + ask("UTM zone (e.g. 19N): ", config_name))
            return parse_projection(ask("EPSG or ESRI code: ", config_name))
        except ValueError as error:
            print(f"  {error}. Please try again.")


def projection_setting(setting, frame_name, config_name, scramble_url, main=None):
    """Projection from the config if set there, otherwise ask."""
    if setting is None:
        return ask_projection(frame_name, config_name, scramble_url, main)
    try:
        return parse_projection(setting, main)
    except ValueError as error:
        raise SystemExit(f"{config_name} = {setting!r}: {error}")


def pretty_name(spatial_reference):
    return spatial_reference.name.replace("_", " ")


# =============================================================================
# Layouts (.pagx files)
# =============================================================================

def page_size(pagx):
    """(width, height) of a .pagx layout's page, or None if unreadable."""
    try:
        page = json.loads(pagx.read_text(encoding="utf-8-sig"))["layoutDefinition"]["page"]
        return page["width"], page["height"]
    except (KeyError, ValueError, OSError):
        return None


def describe_layout(pagx):
    size = page_size(pagx)
    if not size:
        return pagx.stem
    width, height = size
    shape = "landscape" if width > height else "portrait"
    return f"{pagx.stem}  ({shape}, {width:.0f} x {height:.0f} mm)"


def country_shape_hint(admin0, spatial_reference):
    """Sentence on how wide the country is compared with its height."""
    try:
        extent = arcpy.Describe(str(admin0)).extent.projectAs(spatial_reference)
        ratio = extent.width / extent.height
    except Exception:
        return ""
    shape = "landscape" if ratio >= 1 else "portrait"
    return (f"In the Main map projection the country is {ratio:.2f} times as wide as it is "
            f"tall, so a {shape} layout is likely to fit best.")


def choose_layout(paths, hint):
    layouts = sorted(paths.templates.glob("*.pagx"))
    if not layouts:
        raise SystemExit(f"No .pagx layouts found in {paths.templates}")

    if cfg.LAYOUT:
        chosen = paths.templates / f"{cfg.LAYOUT}.pagx"
        if not chosen.is_file():
            raise SystemExit(f"LAYOUT = {cfg.LAYOUT!r}: {chosen.name} not found in {paths.templates}")
        return chosen

    print("\nLayout (from the .pagx files in the templates folder).")
    print("For initial maps, choose a layout that matches the shape (aspect ratio) of the country.")
    if hint:
        print(hint)
    for number, pagx in enumerate(layouts, 1):
        print(f"  {number}: {describe_layout(pagx)}")
    return layouts[choose_number(f"Choose 1-{len(layouts)}: ", 1, len(layouts), "LAYOUT") - 1]


ADMIN_NAME_FIELD = re.compile(r"^ADM([12])_([A-Z]{2})$")


def choose_admin_language(resolved, default="EN"):
    """Language part of the admin 1 and 2 name fields used in labels (EN for
    ADM1_EN, ES for ADM1_ES...). Lists the fields found in the data."""
    if cfg.ADMIN_LABEL_LANGUAGE:
        return cfg.ADMIN_LABEL_LANGUAGE.strip().upper()

    found = set()
    for spec, dataset in resolved.items():
        if re.match(r"admn_ad[12]_py", spec.layer) and dataset.suffix.lower() == ".shp":
            for field in arcpy.ListFields(str(dataset)):
                if ADMIN_NAME_FIELD.match(field.name.upper()):
                    found.add(field.name.upper())

    print("\nAdmin 1 and 2 label language: the xx in the ADM1_xx / ADM2_xx name fields.")
    print(f"  Name fields in the data: {', '.join(sorted(found)) or 'none found'}")
    while True:
        answer = ask(f"Language code [{default}]: ", "ADMIN_LABEL_LANGUAGE").upper()
        answer = re.sub(r"^ADM[12]_", "", answer) or default
        if re.fullmatch(r"[A-Z]{2}", answer):
            return answer
        print("  Please enter a two-letter code such as EN or ES (or ADM1_ES).")


# =============================================================================
# Finding the data for each layer
# =============================================================================

PERMISSION_CODES = {"hh", "hp", "mh", "mm", "mp", "pp"}  # see 200_data_name_lookup/07_permission.csv


def data_source_of(dataset):
    """Source part of a MapAction data file name: the part just before the
    permission code, e.g. 'ine' in ven_admn_ad0_py_s1_ine_pp_country.shp.
    (The scale part is sometimes left out, so the position varies.)"""
    parts = dataset.stem.lower().split("_")
    for index in range(4, len(parts)):
        if parts[index] in PERMISSION_CODES:
            return parts[index - 1]
    return ""


def find_candidates(spec, event, paths):
    prefix = {"country": event.iso3, "world": cfg.WORLD_PREFIX, "region": "reg"}[spec.prefix]
    folder = paths.active_data / spec.folder
    return sorted(p for p in folder.glob(prefix + spec.pattern) if p.is_file())


def ask_user_to_choose(spec, candidates):
    """Ask which dataset to use. Returns None (layer skipped) if no answer can be given."""
    print(f"\nSeveral datasets match '{spec.layer}':")
    for number, candidate in enumerate(candidates, 1):
        print(f"  {number}: {candidate.name}")
    print("  (add your choice to PREFERRED_DATASETS in the config to skip this question)")
    try:
        number = choose_number(f"Choose 1-{len(candidates)}: ", 1, len(candidates), "PREFERRED_DATASETS")
    except SystemExit:
        print(f"  * no answer possible here, skipping '{spec.layer}'")
        return None
    return candidates[number - 1]


def choose_dataset(spec, candidates):
    """Pick one dataset: the only match, else the configured choice, else the
    preferred supplier, else ask."""
    if len(candidates) <= 1:
        return candidates[0] if candidates else None

    preferred = cfg.PREFERRED_DATASETS.get(spec.layer, "").lower()
    if preferred:
        for candidate in candidates:
            if candidate.name.lower() == preferred:
                return candidate
        print(f"  * PREFERRED_DATASETS entry for '{spec.layer}' ({preferred}) matches no dataset")

    from_supplier = [c for c in candidates if data_source_of(c) == cfg.PREFERRED_SUPPLIER]
    if len(from_supplier) == 1:
        return from_supplier[0]

    return ask_user_to_choose(spec, candidates)


def resolve_datasets(specs, event, paths):
    """Return {LayerSpec: dataset Path} for every spec that has data. Layers
    using the same files share one choice, so nobody is asked twice."""
    choices = {}
    resolved = {}
    for spec in specs:
        key = (spec.layer, spec.prefix, spec.pattern, spec.folder)
        if key not in choices:
            choices[key] = choose_dataset(spec, find_candidates(spec, event, paths))
        if choices[key] is not None:
            resolved[spec] = choices[key]
    return resolved


def admin0_dataset(resolved):
    """The affected country's admin 0 polygons, if one of the layers uses them."""
    for spec, dataset in resolved.items():
        if spec.layer.startswith("admn_ad0_py") and dataset.suffix.lower() == ".shp":
            return dataset
    return None


# =============================================================================
# The feather (fade outside the affected country)
# =============================================================================

def feather_file(admin0, event, paths):
    """Feather file name, as made by the Data Scramble toolbox (2.1 Create
    Feather): the admin 0 file's ending after the permission code, e.g.
    ven_admn_ad0_py_s1_ine_pp_country.shp ->
    ven_carto_fea_py_mapaction_pp_faded_country.shp."""
    parts = admin0.stem.split("_")
    ending = "country"
    for index in range(4, len(parts) - 1):
        if parts[index].lower() in PERMISSION_CODES:
            ending = "_".join(parts[index + 1:])
            break
    folder = (paths.active_data / cfg.FEATHER_BACKGROUND).parent
    return folder / f"{event.iso3}_carto_fea_py_mapaction_pp_faded_{ending}.shp"


def make_feather(admin0, event, paths):
    """Make the feather data: the admin 0 polygon erased from the global
    background polygon. Returns the file, or None if it can't be made."""
    background = paths.active_data / cfg.FEATHER_BACKGROUND
    if admin0 is None:
        print("  * no admin 0 polygons in these maps, so no feather")
        return None
    if not background.is_file():
        print(f"  * no feather: global background not found ({background})")
        return None

    target = feather_file(admin0, event, paths)
    newest_input = max(admin0.stat().st_mtime, background.stat().st_mtime)
    if not cfg.TEST_MODE and target.is_file() and target.stat().st_mtime >= newest_input:
        return target
    try:
        with arcpy.EnvManager(overwriteOutput=True, outputMFlag="Disabled", outputZFlag="Disabled"):
            arcpy.analysis.Erase(str(background), str(admin0), str(target))
    except Exception as error:
        if target.is_file():
            print(f"  * could not remake {target.name} (in use?), using the existing file: {error}")
            return target
        print(f"  * could not make the feather {target.name}: {error}")
        return None
    print(f"  made the feather {target.name} from {admin0.name}")
    return target


def feather_symbol():
    """Stacked white fills, each pulled further away from the country's
    border, so the fade builds up gradually (see FEATHER_STEPS)."""
    fills = []
    for step in range(cfg.FEATHER_STEPS):
        offset = arcpy.cim.CreateCIMObjectFromClassName("CIMGeometricEffectOffset", "V3")
        offset.method = "Rounded"
        offset.option = "Accurate"
        offset.offset = -step * cfg.FEATHER_STEP_PT  # negative shrinks the mask, away from the border
        fill = solid_fill([255, 255, 255, cfg.FEATHER_STEP_OPACITY])
        fill.effects = [offset]
        fills.append(fill)
    return polygon_symbol(fills)


def style_feather(layer):
    """Give the feather layer its symbol. The layer file's own symbol is
    replaced: the standard one expects older ring-shaped feather data with
    an 'xpar' transparency field, which the toolbox's feather does not have."""
    definition = layer.getDefinition("V3")
    renderer = arcpy.cim.CreateCIMObjectFromClassName("CIMSimpleRenderer", "V3")
    renderer.symbol = feather_symbol()
    renderer.label = "Feather"
    renderer.patch = "Default"
    definition.renderer = renderer
    layer.setDefinition(definition)


def source_display_names(sources):
    """Marginalia names for data sources ('naturalearth' -> 'Natural Earth')."""
    missing = sorted(s for s in sources if s not in cfg.SOURCE_NAMES)
    if missing:
        print(f"  * no SOURCE_NAMES entry for: {', '.join(missing)} (shown as they are)")
    return sorted(cfg.SOURCE_NAMES.get(s, s) for s in sources)


# =============================================================================
# Checks before building anything
# =============================================================================

def validate_config():
    """Problems in the config that would make layers silently go missing."""
    problems = []
    layers_by_frame = {}
    for spec in cfg.LAYERS:
        layers_by_frame.setdefault(spec.frame, set()).add(spec.layer)
    all_layers = set().union(*layers_by_frame.values())

    for map_spec in cfg.MAPS:
        for name in map_spec.layers:
            if name.lower().endswith((".lyrx", ".lyr")):
                problems.append(f"{map_spec.code}: '{name}' must not include the file extension")
            elif name not in all_layers:
                problems.append(f"{map_spec.code}: '{name}' has no entry in LAYERS")

    for frame, (layer, _) in cfg.FRAME_EXTENTS.items():
        if layer not in layers_by_frame.get(frame, set()):
            problems.append(f"FRAME_EXTENTS: '{layer}' has no entry in LAYERS for '{frame}'")

    codes = [m.code for m in cfg.MAPS]
    for code in cfg.MAPS_TO_RUN or []:
        if code not in codes:
            problems.append(f"MAPS_TO_RUN: '{code}' is not defined in MAPS")
    return problems


def check_layer_files(specs, paths):
    missing = sorted({spec.layer for spec in specs
                      if not (paths.layer_files / (spec.layer + cfg.LAYER_FILE_EXT)).is_file()})
    return [f"layer file missing: {paths.layer_files / (name + cfg.LAYER_FILE_EXT)}" for name in missing]


def check_label_fields(resolved, event, admin_language):
    """Admin polygons must have a name field in the label language: ADM0_xx
    in the event's, ADM1_xx / ADM2_xx in the chosen admin label language.
    Boundary lines are not labelled, so are skipped."""
    warnings = []
    checked = set()
    for spec, dataset in resolved.items():
        match = re.search(r"admn_ad([012])_py_", spec.layer)
        if not match or dataset.suffix.lower() != ".shp" or dataset in checked:
            continue
        checked.add(dataset)
        level = match.group(1)
        field = f"ADM{level}_{event.language if level == '0' else admin_language}"
        fields = [f.name.upper() for f in arcpy.ListFields(str(dataset))]
        if field not in fields:
            warnings.append(f"{dataset.name}: no '{field}' field, so labels using admin names keep "
                            f"their current language (has: {', '.join(fields)})")
    return warnings


def country_name(admin0, event):
    """Country name for the map: from the config, else from the admin 0 data."""
    if cfg.COUNTRY_NAME:
        return cfg.COUNTRY_NAME
    field = f"ADM0_{event.language}"
    if admin0 is not None:
        try:
            with arcpy.da.SearchCursor(str(admin0), [field]) as cursor:
                for (value,) in cursor:
                    if value and value.strip():
                        return value.strip()
        except RuntimeError:
            pass
    print(f"  * could not read the country name ({field}); using '{event.iso3.upper()}'."
          " Set COUNTRY_NAME in the config to override.")
    return event.iso3.upper()


# =============================================================================
# Testing mode
# =============================================================================

def clear_outputs(paths):
    """Delete every map-code output folder this script can produce."""
    if not (paths.root / TEST_MARKER).is_file():
        raise RuntimeError(
            f"TEST_MODE is on, but {paths.root} has no {TEST_MARKER} file. Testing mode deletes "
            "outputs, so it only runs in a test copy of a project. Set TEST_MODE = False to "
            "run on a live project.")
    for map_spec in cfg.MAPS:
        for base in (paths.map_projects, paths.map_exports):
            folder = base / map_spec.code
            if folder.exists():
                try:
                    shutil.rmtree(folder)
                except PermissionError as error:
                    raise SystemExit(f"\nCannot delete {error.filename}: it is open in another "
                                     "program (usually ArcGIS Pro). Close it and run again.")
                print(f"  deleted {folder.relative_to(paths.root)}")


# =============================================================================
# Working with layers
# =============================================================================

def add_layer(map_obj, layer_file, name):
    """Add the first layer of a .lyrx to the bottom of a map, renamed to the
    config name so it can be found again by name."""
    try:
        layer = arcpy.mp.LayerFile(str(layer_file)).listLayers()[0]
    except Exception as error:
        print(f"  * could not load {layer_file.name}: {error}")
        return None
    layer.name = name
    map_obj.addLayer(layer, "BOTTOM")
    # addLayer adds a copy; return the one now in the map.
    return map_obj.listLayers(name)[-1]


def point_layer_at(layer, dataset):
    """Repoint a layer at a shapefile or raster in a folder workspace."""
    if not layer.supports("DATASOURCE"):
        return
    current = layer.connectionProperties
    new = dict(current)
    new["connection_info"] = dict(current.get("connection_info", {}), database=str(dataset.parent))
    # Shapefiles are named without their extension; rasters keep it.
    new["dataset"] = dataset.stem if dataset.suffix.lower() == ".shp" else dataset.name
    try:
        layer.updateConnectionProperties(current, new)
    except Exception as error:
        print(f"  * could not link {layer.name} to {dataset.name}: {error}")


def set_label_language(layer, language, admin_language):
    """Rewrite ADMn_xx field names in a layer's label expressions: ADM0_xx to
    the event language, ADM1_xx and ADM2_xx to the chosen admin label
    language. Works for VBScript ([ADM1_EN]), Python (!ADM1_EN!) and Arcade
    ($feature.ADM1_EN) expressions. A field is only switched if the data has
    it."""
    if not (layer.supports("ISFEATURELAYER") and layer.isFeatureLayer):
        return
    fields = {f.name.upper() for f in arcpy.ListFields(layer)}
    pattern = re.compile(r"\bADM([012])_[A-Za-z]{2}\b", re.IGNORECASE)

    def switch(match):
        level = match.group(1)
        wanted = f"ADM{level}_{language if level == '0' else admin_language}"
        return wanted if wanted in fields else match.group(0)

    for label_class in layer.listLabelClasses():
        expression = label_class.expression or ""
        new_expression = pattern.sub(switch, expression)
        if new_expression != expression:
            label_class.expression = new_expression


def save_with_retry(aprx, attempts=5, delay=1.5):
    """Save, retrying while a sync client (e.g. Nextcloud) briefly locks the file."""
    for attempt in range(1, attempts + 1):
        try:
            aprx.save()
            return
        except OSError:
            if attempt == attempts:
                raise
            print(f"  * save failed (file locked?), retrying in {delay}s")
            time.sleep(delay)


# =============================================================================
# Layout styling
# =============================================================================

def solid_fill(rgba):
    """CIM solid fill symbol layer; rgba is [red, green, blue, opacity %]."""
    color = arcpy.cim.CreateCIMObjectFromClassName("CIMRGBColor", "V3")
    color.values = list(rgba)
    fill = arcpy.cim.CreateCIMObjectFromClassName("CIMSolidFill", "V3")
    fill.enable = True
    fill.color = color
    return fill


def polygon_symbol(symbol_layers):
    """CIM symbol reference for a polygon symbol made of these layers."""
    polygon = arcpy.cim.CreateCIMObjectFromClassName("CIMPolygonSymbol", "V3")
    polygon.symbolLayers = symbol_layers
    reference = arcpy.cim.CreateCIMObjectFromClassName("CIMSymbolReference", "V3")
    reference.symbol = polygon
    return reference


def white_fill(opacity=100):
    """CIM symbol reference for a plain white fill (opacity in percent)."""
    return polygon_symbol([solid_fill([255, 255, 255, opacity])])


def all_elements(elements):
    """Layout CIM elements, including those inside groups."""
    for element in elements:
        yield element
        if type(element).__name__ == "CIMGroupElement":
            yield from all_elements(element.elements)


def fill_legend(layout, main_map):
    """List the Main map's layers in the layout's legend, in drawing order,
    except those in LEGEND_EXCLUDE."""
    legends = layout.listElements("LEGEND_ELEMENT")
    if not legends:
        print("  * this layout has no legend")
        return
    legend = legends[0]
    legend.syncNewLayer = False
    for item in list(legend.items):
        legend.removeItem(item)
    for layer in main_map.listLayers():
        if layer.name not in cfg.LEGEND_EXCLUDE and not layer.isGroupLayer:
            legend.addItem(layer, "BOTTOM")
            if layer.name in cfg.LEGEND_HEADINGS:
                set_legend_heading(layer, cfg.LEGEND_HEADINGS[layer.name])


def set_legend_heading(layer, text):
    """Set the heading a layer shows in legends: the raster colorizer's
    heading, or the feature renderer's. style_layout makes it visible."""
    cim = layer.getDefinition("V3")
    target = getattr(cim, "colorizer", None) or getattr(cim, "renderer", None)
    if target is None or not hasattr(target, "heading"):
        print(f"  * cannot set the legend heading of {layer.name}")
        return
    target.heading = text
    layer.setDefinition(cim)


def style_layout(layout):
    """White backgrounds for the legend and every text box, except text in
    GROUP_BACKGROUNDS groups, which share one background for the group.
    Legend entries show the symbol labels only (layer names are config
    codes), the legend has LEGEND_COLUMNS_LANDSCAPE or _PORTRAIT columns,
    and its frame shrinks or grows to fit them."""
    definition = layout.getDefinition("V3")
    in_group = set()  # ids of elements inside a GROUP_BACKGROUNDS group
    # all_elements yields each group before its members.
    for element in all_elements(definition.elements):
        kind = type(element).__name__
        if kind == "CIMGroupElement" and element.name in cfg.GROUP_BACKGROUNDS:
            in_group.update(id(member) for member in all_elements(element.elements))
            if element.graphicFrame is None:
                element.graphicFrame = arcpy.cim.CreateCIMObjectFromClassName("CIMGraphicFrame", "V3")
            frame = element.graphicFrame
            frame.backgroundSymbol = white_fill(cfg.GROUP_BACKGROUNDS[element.name])
            frame.backgroundGapX = frame.backgroundGapY = 2
            continue
        is_text = (kind == "CIMGraphicElement"
                   and type(element.graphic).__name__ == "CIMParagraphTextGraphic")
        if is_text and id(element) in in_group:
            if element.graphic.frame is not None:
                element.graphic.frame.backgroundSymbol = None
            continue
        if kind == "CIMLegend":
            frame = element.graphicFrame
            element.fittingStrategy = "AdjustFrame"
            landscape = layout.pageWidth > layout.pageHeight
            element.columns = cfg.LEGEND_COLUMNS_LANDSCAPE if landscape else cfg.LEGEND_COLUMNS_PORTRAIT
            for item in element.items:
                item.showLayerName = False
                item.showHeading = item.name in cfg.LEGEND_HEADINGS
            gap = 2
        elif is_text:
            if element.graphic.frame is None:
                element.graphic.frame = arcpy.cim.CreateCIMObjectFromClassName("CIMGraphicFrame", "V3")
            frame = element.graphic.frame
            gap = 1
        else:
            continue
        frame.backgroundSymbol = white_fill()
        frame.backgroundGapX = frame.backgroundGapY = gap
    layout.setDefinition(definition)


def update_text(layout, map_spec, version, event, country, sources, main_projection):
    """Fill in the layout's text elements."""
    texts = {
        "title": map_spec.title,
        "summary": map_spec.summary,
        "map_no": f"{map_spec.code} {version}",
        "country": country,
        "glide_no": event.glide,
        "time_zone": event.time_zone,
        "create_date_time": time.strftime("%d %b %Y / %H:%M"),
        "data_sources": ", ".join(source_display_names(sources)),
        "map_producer": event.producer,
        "disclaimer": event.disclaimer,
        "donor_credit": event.donor_credits,
        "spatial_reference": pretty_name(main_projection),
    }
    for element in layout.listElements("TEXT_ELEMENT"):
        if texts.get(element.name):
            element.text = texts[element.name]


# =============================================================================
# Building one map
# =============================================================================

@dataclass(frozen=True)
class RunChoices:
    """Everything decided once at the start and used for every map."""
    template: Path
    layout: Path            # .pagx file
    main_projection: object  # arcpy.SpatialReference
    location_projection: object
    country: str
    admin_language: str      # upper case, for ADM1_xx / ADM2_xx label fields


def next_version(paths, map_code):
    """Next free version, e.g. 'v03' if MA901-v02-... exists."""
    pattern = re.compile(rf"^{re.escape(map_code)}-v(\d+)-", re.IGNORECASE)
    versions = [int(m.group(1))
                for f in (paths.map_projects / map_code).rglob("*")
                if (m := pattern.match(f.name))]
    return f"v{max(versions, default=0) + 1:02d}"


def set_project_defaults(aprx, target, paths):
    """Home folder, default geodatabase and default toolbox. The template's
    own point at the project it was made in, so ArcGIS Pro would ask for them
    each time the new project is opened."""
    aprx.homeFolder = str(target.parent)
    for setting, path in (("defaultGeodatabase", paths.default_geodatabase()),
                          ("defaultToolbox", paths.default_toolbox())):
        if path.exists():
            setattr(aprx, setting, str(path))


def create_project(template, pagx, target, paths):
    """New project from the template, with the template's maps and layouts
    replaced by the chosen .pagx layout (which brings its own Main map and
    Location map). saveACopy gives the copy new internal IDs, so it stays
    independent of the template even if that is open in ArcGIS Pro."""
    target.parent.mkdir(parents=True, exist_ok=True)
    template_project = arcpy.mp.ArcGISProject(str(template))
    template_project.saveACopy(str(target))
    del template_project
    target.chmod(stat.S_IWRITE | stat.S_IREAD)  # templates are often read-only

    aprx = arcpy.mp.ArcGISProject(str(target))
    set_project_defaults(aprx, target, paths)  # first, so nothing is written to the template's old folders
    for layout in aprx.listLayouts():
        aprx.deleteItem(layout)
    for map_obj in aprx.listMaps():
        aprx.deleteItem(map_obj)
    aprx.importDocument(str(pagx))
    save_with_retry(aprx)
    del aprx


def add_map_layers(aprx, map_spec, resolved, paths):
    """Add and link the layers of one map. Returns the data sources used."""
    specs_by_frame = {(s.frame, s.layer): s for s in resolved}
    sources = set()
    for map_obj in aprx.listMaps():
        for name in map_spec.layers:
            spec = specs_by_frame.get((map_obj.name, name))
            if spec is None:
                continue
            layer = add_layer(map_obj, paths.layer_files / (name + cfg.LAYER_FILE_EXT), name)
            if layer is None:
                continue
            point_layer_at(layer, resolved[spec])
            if name == cfg.FEATHER_LAYER:
                try:
                    style_feather(layer)
                except Exception as error:
                    print(f"  * could not style the feather: {error}")
            sources.add(data_source_of(resolved[spec]))
    return sources


def finish_maps(aprx, map_spec, resolved, event, choices):
    """Projections, label language and country filters. Run on a freshly
    reopened project: label classes only see the new data's fields after a
    save and reopen."""
    projections = {MAIN: choices.main_projection, LOCATION: choices.location_projection}
    for map_obj in aprx.listMaps():
        if map_obj.name in projections:
            map_obj.spatialReference = projections[map_obj.name]

    for spec in resolved:
        if spec.layer not in map_spec.layers:
            continue
        for map_obj in aprx.listMaps(spec.frame):
            for layer in map_obj.listLayers(spec.layer):
                try:
                    set_label_language(layer, event.language, choices.admin_language)
                except Exception as error:
                    print(f"  * could not set label language on {layer.name}: {error}")
                if layer.supports("DEFINITIONQUERY"):
                    if spec.exclude_affected_country:
                        # ISO3CD holds a country code (VEN) or, for boundary lines, a pair (COL_VEN).
                        layer.definitionQuery = f"ISO3CD NOT LIKE '%{event.iso3.upper()}%'"
                    elif spec.only_affected_country:
                        layer.definitionQuery = f"{spec.only_affected_country} = '{event.iso3.lower()}'"
                if not spec.labels and layer.supports("SHOWLABELS"):
                    layer.showLabels = False


def frame_cameras(layout):
    """{map name: (x, y, scale, width, height)} of each map frame's view, in
    the map's coordinates, so the map tabs can open at the same view."""
    cameras = {}
    for frame in layout.listElements("MAPFRAME_ELEMENT"):
        if frame.map is None:
            continue
        camera = frame.camera
        extent = camera.getExtent()
        cameras[frame.map.name] = (camera.X, camera.Y, camera.scale, extent.width, extent.height)
    return cameras


def pane_layout_xml(tabs, active):
    """ArcGIS Pro's saved window layout: the Contents pane on the left, the
    Catalog pane on the right, and the given tabs open in the middle.
    tabs is a list of (pane name, view id)."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    contents, catalog = str(uuid.uuid4()), str(uuid.uuid4())
    windows = [(str(uuid.uuid4()), name, view_id) for name, view_id in tabs]
    selected = next(unique for unique, name, _ in windows if name == active)
    refs = "".join(f'<UIElement xsi:type="DocumentWindowRef" UniqueId="{unique}" />'
                   for unique, _, _ in windows)
    documents = "".join(
        f'<DocumentWindow UniqueId="{unique}" SerializationId="{name}" Name="{name}" '
        f'ContainerDockedSize="1200,800" IsOpen="true" '
        f'LastActiveDateTime="{now}.{"9" if name == active else "0"}" State="Document">'
        f'<Tag xsi:type="xsd:unsignedInt">{view_id}</Tag></DocumentWindow>'
        for unique, name, view_id in windows)
    tool_windows = "".join(
        f'<ToolWindow UniqueId="{unique}" SerializationId="{name}" Name="{name}" '
        f'ContainerDockedSize="300,800" IsOpen="true" LastActiveDateTime="{now}" State="Docked">'
        f'<Tag xsi:type="xsd:boolean">true</Tag></ToolWindow>'
        for unique, name in ((contents, "esri_core_contentsDockPane"),
                             (catalog, "esri_core_projectDockPane")))
    dock_site = (
        '<DockSiteLayout xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        'xmlns:xsd="http://www.w3.org/2001/XMLSchema" SerializationFormat="All" Version="2">'
        '<AutoHideHost />'
        '<Content xsi:type="SplitContainer" Orientation="Horizontal" DockedSize="1800,800">'
        f'<UIElement xsi:type="ToolWindowContainer" DockedSize="300,800" SelectedWindowUniqueId="{contents}">'
        f'<UIElement xsi:type="ToolWindowRef" UniqueId="{contents}" /></UIElement>'
        '<UIElement xsi:type="Workspace"><Content xsi:type="TabbedMdiHost">'
        f'<Content xsi:type="TabbedMdiContainer" DockedSize="1200,800" SelectedWindowUniqueId="{selected}">'
        f'{refs}</Content></Content></UIElement>'
        f'<UIElement xsi:type="ToolWindowContainer" DockedSize="300,800" SelectedWindowUniqueId="{catalog}">'
        f'<UIElement xsi:type="ToolWindowRef" UniqueId="{catalog}" /></UIElement>'
        '</Content>'
        f'<DocumentWindows>{documents}</DocumentWindows>'
        f'<ToolWindows>{tool_windows}</ToolWindows>'
        '</DockSiteLayout>')
    return (f"<esriPaneState>\n  <PaneState>{xml_escape(dock_site)}</PaneState>\n"
            f"  <ActivePane>{active}</ActivePane>\n</esriPaneState>")


def edit_project_json(project_file, edit):
    """Edit a closed .aprx's GISProject.json (project items, default
    geodatabase, open views...). An .aprx is a zip file; `edit` is called
    with the parsed JSON and changes it in place."""
    with zipfile.ZipFile(project_file) as archive:
        entries = [(info, archive.read(info)) for info in archive.infolist()]
    index = next(i for i, (info, _) in enumerate(entries) if info.filename == "GISProject.json")
    raw = entries[index][1]
    bom = raw.startswith(b"\xef\xbb\xbf")
    project = json.loads(raw.decode("utf-8-sig"))
    result = edit(project)
    text = json.dumps(project, indent=2, ensure_ascii=False).encode("utf-8")
    entries[index] = (entries[index][0], (b"\xef\xbb\xbf" if bom else b"") + text)

    temporary = project_file.with_suffix(".aprx.tmp")
    with zipfile.ZipFile(temporary, "w") as archive:
        for info, data in entries:
            archive.writestr(info, data, compress_type=info.compress_type)
    temporary.replace(project_file)
    return result


# Project items that only record past work (tool history, notebooks), and
# items that point at files or folders.
HISTORY_ITEM_TYPES = {"GPHistory", "RFxHistory", "Notebook"}
FILE_ITEM_TYPES = {"FolderConnection", "GDB", "GP", "Style"}
GIS_FOLDER_IN_PATH = re.compile(r"(?:^|[\\/])GIS(?:[\\/]|$)", re.IGNORECASE)


def item_target(path_text, folder, gis_folder):
    """Where a project item's path should point, or None if nothing is there.
    A path into a GIS folder (e.g. of the project a template was made in) is
    moved to the same place in this project's GIS folder when that exists,
    even if the old place exists too."""
    match = GIS_FOLDER_IN_PATH.search(path_text)
    if match:
        moved = Path(os.path.normpath(gis_folder / path_text[match.end():]))
        if moved.exists():
            return moved
    path = Path(path_text)
    path = Path(os.path.normpath(path if path.is_absolute() else folder / path))
    return path if path.exists() else None


def relative_to(path, folder):
    try:
        return os.path.relpath(path, folder)
    except ValueError:  # different drive
        return str(path)


def clean_project_items(project, folder, gis_folder):
    """Remove clutter a project inherits from its template: tool and notebook
    history, connections to files that don't exist, and duplicates. Paths
    into another project's GIS folder are moved to this one where the file
    exists. `folder` holds the .aprx. Returns the number of items removed."""
    kept, seen = [], set()
    items = project.get("projectItems", [])
    for item in items:
        kind = item.get("itemType")
        if kind in HISTORY_ITEM_TYPES:
            continue
        path_text = item.get("catalogPath") or ""
        is_file = kind in FILE_ITEM_TYPES and (
            "\\" in path_text or "/" in path_text or path_text.lower().endswith(".stylx"))
        if is_file:  # built-in styles ("ArcGIS 2D") are names, not files
            target = item_target(path_text, folder, gis_folder)
            key = (kind, os.path.normcase(str(target)))
            if target is None or key in seen:
                continue
            seen.add(key)
            item["catalogPath"] = relative_to(target, folder)
            item["pathHint"] = str(target)
            if any(separator in item.get("name", "") for separator in "\\/"):
                item["name"] = target.name
        kept.append(item)
    project["projectItems"] = kept
    return len(items) - len(kept)


def set_default_items(project, folder, paths):
    """Point the project's default geodatabase, toolbox and home folder at
    this CMF (in the JSON; for a closed project such as the template), and
    make sure both appear in the Catalog pane."""
    project["defaultGeoDatabase"] = relative_to(paths.default_geodatabase(), folder)
    project["defaultToolbox"] = relative_to(paths.default_toolbox(), folder)
    project["defaultFolder"] = "."
    present = {(item.get("itemType"), os.path.normcase(item.get("pathHint", "")))
               for item in project.get("projectItems", [])}
    for kind, target in (("GDB", paths.default_geodatabase()), ("GP", paths.default_toolbox())):
        if target.exists() and (kind, os.path.normcase(str(target))) not in present:
            project["projectItems"].append({
                "type": "CIMProjectItem", "iD": str(uuid.uuid4()),
                "catalogPath": relative_to(target, folder), "pathHint": str(target),
                "itemType": kind, "name": target.stem, "pathSaveRelative": True,
            })


def finish_project_file(project_file, cameras, layout_name, page, paths):
    """Final edits to the saved, closed project: remove the template's clutter
    (see clean_project_items) and set the tabs ArcGIS Pro opens. arcpy can't
    do either outside a running ArcGIS Pro, so GISProject.json is edited
    directly."""
    def edit(project):
        removed = clean_project_items(project, project_file.parent, paths.root / "GIS")
        open_views_on_start(project, cameras, layout_name, page)
        return removed
    return edit_project_json(project_file, edit)


def open_views_on_start(project, cameras, layout_name, page):
    """Open the Main map, Location map and layout as tabs when the project
    is opened, the maps at their map frames' views, with the layout in front.
    The open views and window layout are in GISProject.json."""
    paths_by_name = {(item.get("itemType"), item.get("name")): item.get("catalogPath")
                     for item in project.get("projectItems", [])}
    views, tabs = [], []
    for view_id, map_name in enumerate((MAIN, LOCATION), 1):
        path = paths_by_name.get(("Map", map_name))
        if not path or map_name not in cameras:
            continue
        x, y, scale, width, height = cameras[map_name]
        views.append({
            "type": "CIMMapView", "viewableObjectPath": path, "viewType": "esri_mapping_mapPane",
            "instanceID": view_id, "viewingMode": "Map",
            "camera": {"type": "CIMViewCamera", "pitch": -90, "scale": scale, "x": x, "y": y,
                       "z": "NaN", "viewportWidth": width, "viewportHeight": height},
        })
        tabs.append((f"esri_mapping_mapPane_{view_id}", view_id))
    layout_path = paths_by_name.get(("Layout", layout_name))
    if layout_path:
        view_id = len(views) + 1
        width, height = page
        margin = max(width, height) * 0.05
        views.append({
            "type": "CIMLayoutView", "viewableObjectPath": layout_path,
            "viewType": "esri_layouts_layoutPane", "instanceID": view_id,
            "extent": {"xmin": -margin, "ymin": -margin, "xmax": width + margin, "ymax": height + margin},
            "defaultMapFrameName": MAIN,
        })
        tabs.append((f"esri_layouts_layoutPane_{view_id}", view_id))
    if not tabs:
        print("  * could not set the tabs to open: maps and layout not found in the project")
        return

    project["views"] = views
    project["viewLayoutXML"] = pane_layout_xml(tabs, active=tabs[-1][0])


def round_scale_up(scale, fraction=None):
    """Round a scale up to a tidy figure. The step is the value in the series
    1, 2, 5, 10, 20, 50, ... closest (by ratio) to scale * fraction
    (default SCALE_ROUNDING_FRACTION). Returns (rounded scale, step)."""
    if fraction is None:
        fraction = cfg.SCALE_ROUNDING_FRACTION
    target = max(scale * fraction, 1)
    exponent = math.floor(math.log10(target))
    steps = [m * 10 ** e for e in (exponent - 1, exponent, exponent + 1) for m in (1, 2, 5)
             if m * 10 ** e >= 1]
    step = min(steps, key=lambda s: abs(math.log(s / target)))
    return math.ceil(scale / step) * step, step


def zoom_frames(aprx, layout):
    """Zoom each map frame to its extent layer (see FRAME_EXTENTS), then
    multiply its scale and round it up (see round_scale_up)."""
    for frame_name, (layer_name, multiplier) in cfg.FRAME_EXTENTS.items():
        frames = layout.listElements("MAPFRAME_ELEMENT", frame_name)
        maps = aprx.listMaps(frame_name)
        layers = maps[0].listLayers(layer_name) if maps else []
        if not frames or not layers:
            print(f"  * cannot zoom '{frame_name}': frame or layer '{layer_name}' not found")
            continue
        frame = frames[0]
        try:
            frame.camera.setExtent(frame.getLayerExtent(layers[0], False))
            fitted = frame.camera.scale
            rounded, step = round_scale_up(fitted * multiplier)
            frame.camera.scale = rounded
            times = f" x {multiplier} = 1:{fitted * multiplier:,.0f}" if multiplier != 1 else ""
            print(f"  {frame_name} scale: fitted 1:{fitted:,.0f}{times}, "
                  f"rounded up (step {step:,}) to 1:{rounded:,}")
        except Exception as error:
            print(f"  * could not zoom '{frame_name}' to {layer_name}: {error}")


MM_PER_PAGE_UNIT = {"MILLIMETER": 1, "CENTIMETER": 10, "INCH": 25.4, "POINT": 25.4 / 72}


def nice_up(value):
    """The smallest number of the form d x 10^n (d = 1..9) that is >= value."""
    power = 10 ** math.floor(math.log10(value))
    digit = math.ceil(round(value / power, 9))
    return digit * power if digit < 10 else 10 * power


def fit_scale_bar(layout):
    """Set the Main map's scale bar to one division of a nice number of km,
    at least SCALE_BAR_MIN_WIDTH of the page wide, keeping its alignment."""
    bars = layout.listElements("MAPSURROUND_ELEMENT", cfg.SCALE_BAR_NAME)
    frames = layout.listElements("MAPFRAME_ELEMENT", MAIN)
    if not bars or not frames:
        print(f"  * cannot fit the scale bar: '{cfg.SCALE_BAR_NAME}' or '{MAIN}' frame not found")
        return
    bar = bars[0]
    try:
        page_mm = layout.pageWidth * MM_PER_PAGE_UNIT[layout.pageUnits]
        scale = frames[0].camera.scale
        min_km = page_mm * cfg.SCALE_BAR_MIN_WIDTH * scale / 1e6
        km = nice_up(min_km)
        # The bar's position is that of its anchor (left, right or centre, as
        # set in the layout); put it back after resizing to keep that alignment.
        anchor_x, anchor_y = bar.elementPositionX, bar.elementPositionY
        cim = bar.getDefinition("V3")
        cim.units = {"uwkid": 9036}  # kilometres
        cim.division, cim.divisions, cim.subdivisions = km, 1, 0
        cim.divisionsBeforeZero = 0
        cim.fittingStrategy = "AdjustFrame"  # the frame follows the bar's length
        cim.unitLabel = cfg.SCALE_BAR_UNIT_LABEL
        for text in (cim.labelSymbol, cim.unitLabelSymbol):
            if text is not None and text.symbol is not None:
                text.symbol.height *= cfg.SCALE_BAR_TEXT_SIZE_FACTOR
        bar.setDefinition(cim)
        bar.elementPositionX, bar.elementPositionY = anchor_x, anchor_y
        width_mm = km * 1e6 / scale
        print(f"  scale bar: {km:g} km, {width_mm:.1f} mm wide "
              f"(at least {min_km:.1f} km = {cfg.SCALE_BAR_MIN_WIDTH:.0%} of the page width)")
    except Exception as error:
        print(f"  * could not fit the scale bar: {error}")


def build_map(map_spec, resolved, event, choices, paths):
    print(f"\n--- {map_spec.code}: {map_spec.title}")
    version = next_version(paths, map_spec.code)
    base_name = f"{map_spec.code}-{version}-{map_spec.output_name}"
    project_file = paths.map_projects / map_spec.code / f"{base_name}.aprx"
    jpeg_file = paths.map_exports / map_spec.code / version / f"{base_name}.jpg"
    jpeg_file.parent.mkdir(parents=True, exist_ok=True)

    create_project(choices.template, choices.layout, project_file, paths)

    # 1. Add the layers, save, and close the project.
    aprx = arcpy.mp.ArcGISProject(str(project_file))
    sources = add_map_layers(aprx, map_spec, resolved, paths)
    save_with_retry(aprx)
    del aprx
    gc.collect()  # releases arcpy's file lock on the .aprx

    # 2. Reopen, then finish the maps, zoom, legend, styling, text, export.
    aprx = arcpy.mp.ArcGISProject(str(project_file))
    finish_maps(aprx, map_spec, resolved, event, choices)
    layout = aprx.listLayouts()[0]
    zoom_frames(aprx, layout)
    fit_scale_bar(layout)
    fill_legend(layout, aprx.listMaps(MAIN)[0])
    style_layout(layout)
    update_text(layout, map_spec, version, event, choices.country, sources, choices.main_projection)
    save_with_retry(aprx)
    layout.exportToJPEG(str(jpeg_file), resolution=event.jpeg_dpi)
    cameras = frame_cameras(layout)
    layout_name, page = layout.name, (layout.pageWidth, layout.pageHeight)
    del layout, aprx
    gc.collect()

    # 3. Remove the template's clutter; open the maps and layout as tabs.
    try:
        removed = finish_project_file(project_file, cameras, layout_name, page, paths)
        print(f"  removed {removed} leftover project items inherited from the template")
    except Exception as error:
        print(f"  * could not tidy the project or set its tabs: {error}")

    print(f"  project: {project_file.relative_to(paths.root)}")
    print(f"  jpeg:    {jpeg_file.relative_to(paths.root)}")
    return project_file, jpeg_file


# =============================================================================
# Main
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="MapAction map automation for ArcGIS Pro.")
    parser.add_argument("--project", type=Path,
                        help="project folder (default: the one containing this script)")
    return parser.parse_args()


def main():
    start = time.time()
    args = parse_args()
    root = find_project_root((args.project or script_dir()).absolute())
    paths = ProjectPaths.from_root(root)
    event = Event.from_json(root / "event_description.json")
    print(f"Map automation for {event.operation_id} ({root})")
    print(f"Language {event.language}, GLIDE {event.glide}, test mode {'ON' if cfg.TEST_MODE else 'off'}")

    problems = validate_config()
    if problems:
        print("\nConfig problems:")
        for problem in problems:
            print("  -", problem)
        raise SystemExit("Fix map_automation_pro_config.py and run again.")

    template = paths.templates / cfg.TEMPLATE_FILE
    if not template.is_file():
        raise SystemExit(f"Template not found: {template}")

    maps = [m for m in cfg.MAPS if cfg.MAPS_TO_RUN is None or m.code in cfg.MAPS_TO_RUN]
    used_names = {name for m in maps for name in m.layers}
    specs = [s for s in cfg.LAYERS if s.layer in used_names]

    # Data first: choosing datasets may need questions too.
    print("\nFinding data")
    feather_specs = [s for s in specs if s.layer == cfg.FEATHER_LAYER]
    resolved = resolve_datasets([s for s in specs if s not in feather_specs], event, paths)
    if feather_specs:
        feather = make_feather(admin0_dataset(resolved), event, paths)
        if feather:
            resolved.update({spec: feather for spec in feather_specs})
    for spec, dataset in resolved.items():
        print(f"  {spec.frame:12} {spec.layer:32} -> {dataset.name}")

    # Questions for the whole run.
    scramble_url = paths.data_scramble_sheet_url()
    main_projection = projection_setting(cfg.MAIN_MAP_PROJECTION, MAIN, "MAIN_MAP_PROJECTION", scramble_url)
    location_projection = projection_setting(cfg.LOCATION_MAP_PROJECTION, LOCATION,
                                             "LOCATION_MAP_PROJECTION", scramble_url, main=main_projection)
    admin0 = admin0_dataset(resolved)
    hint = country_shape_hint(admin0, main_projection) if admin0 else ""
    layout = choose_layout(paths, hint)
    admin_language = choose_admin_language(resolved)
    choices = RunChoices(template, layout, main_projection, location_projection,
                         country_name(admin0, event), admin_language)

    print(f"\nMain map:     {pretty_name(main_projection)}")
    print(f"Location map: {pretty_name(location_projection)}")
    print(f"Layout:       {layout.stem}")
    print(f"Country:      {choices.country}")
    print(f"Admin labels: ADM1_{admin_language} / ADM2_{admin_language}")

    warnings = check_layer_files(specs, paths) + check_label_fields(resolved, event, admin_language)
    warnings += [f"{path} not found, so ArcGIS Pro will ask for it when a new project is opened"
                 for path in (paths.default_geodatabase(), paths.default_toolbox()) if not path.exists()]
    warnings += [f"no data found for '{s.layer}' ({s.frame}): {s.prefix} {s.pattern} in {s.folder}"
                 for s in specs if s not in resolved]
    if warnings:
        print("\nWarnings (these maps will still be built):")
        for warning in warnings:
            print("  -", warning)

    if cfg.TEST_MODE:
        print("\nTest mode: deleting previous outputs")
        clear_outputs(paths)

    for map_spec in maps:
        map_resolved = {s: d for s, d in resolved.items() if s.layer in map_spec.layers}
        build_map(map_spec, map_resolved, event, choices, paths)

    print(f"\nDone: {len(maps)} map(s) in {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
