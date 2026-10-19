"""Settings for map_automation_pro.py.

Event details (country ISO3, GLIDE number, time zone, language, producer
contact, disclaimer, donor credits, JPEG resolution) are NOT set here: they
are read from event_description.json at the root of the project folder.
This file only holds what is specific to the map automation itself.
"""

from typing import NamedTuple


# --- What to run ------------------------------------------------------------

# Testing mode deletes every previous output of this script (the map-code
# folders in 33_Map_Projects and 34_Map_Products_MapAction) before running,
# so each run starts clean. It only works in a project folder that contains a
# TEST_ENVIRONMENT.txt file, so it can never wipe outputs in a live project.
TEST_MODE = True

# Map codes to build on this run. None builds every map in MAPS below.
MAPS_TO_RUN = ["MA901"]


# --- Questions asked at the start of a run ------------------------------------
# Leave a setting as None to be asked each run, or fill it in to skip the question.

# Projection of the Main map. "WGS84" (ArcGIS Pro default: latitude/longitude),
# a UTM zone such as "UTM 19N", or an EPSG/ESRI code such as "EPSG:32619".
MAIN_MAP_PROJECTION = None

# Projection of the Location map: as above, or "SAME" for the Main map's.
LOCATION_MAP_PROJECTION = None

# Layout: name of a .pagx file in <map_templates>/321_arcpro, without the
# extension, e.g. "landscape_a3_marginalia_inside".
LAYOUT = None


# --- Template ---------------------------------------------------------------

# Base project in <map_templates>/321_arcpro. Each map starts as a copy of it;
# its own maps and layouts are replaced by the chosen .pagx layout.
TEMPLATE_FILE = "arcpro_templates_automation_test.aprx"


# --- Folders inside the standard project structure ---------------------------

# Base folders come from cmf_description.json; these ArcGIS Pro subfolders sit
# inside them.
LAYER_FILES_SUBFOLDER = "3121_arcpro"   # inside 312_Layer_files
TEMPLATES_SUBFOLDER = "321_arcpro"      # inside 32_Map_Templates
LAYER_FILE_EXT = ".lyrx"


# --- Data selection ---------------------------------------------------------

# Prefix of global datasets (e.g. wrl_admn_adx_py_..._worldcountries.shp).
WORLD_PREFIX = "wrl"

# When a layer's file pattern matches several datasets, the one from this
# source (6th part of the file name, e.g. ven_admn_ad0_py_s1_<ine>_pp...) wins.
PREFERRED_SUPPLIER = "ine"

# Fixed dataset choices for layers whose pattern matches several files.
# Checked before PREFERRED_SUPPLIER. Anything still ambiguous is asked for
# at the start of the run.
PREFERRED_DATASETS = {
    "stle_stl_pt_natearth_cap-city": "ven_stle_stl_pt_s0_naturalearth_pp_maincities.shp",
    "tran_air_pt_ourairports_lge-med": "ven_tran_air_pt_s1_ourairports_pp.shp",
    "phys_lak_py_all": "ven_phys_lak_py_s1_naturalearth_pp.shp",
    "admn_ad1_py_all_reference": "ven_admn_ad1_py_s1_ine_pp_state_fixGeom.shp",
    "admn_ad2_py_all_reference": "ven_admn_ad2_py_s1_ine_pp_municipality.shp",
    "tran_rrd_ln_all": "ven_tran_rrd_ln_s0_naturalearth_pp.shp",
}

# Country name shown on the map. None reads it from the admin 0 data, using
# the ADM0_<language> field (language from event_description.json).
COUNTRY_NAME = None

# How each data source (the lower-case source part of data file names, e.g.
# ven_admn_ad0_py_s1_<ine>_pp_country.shp) is written in the map's data
# sources text. Sources missing here are shown as they are, with a warning.
SOURCE_NAMES = {
    "gmted": "GMTED",
    "ine": "INE",
    "mapaction": "MapAction",
    "naturalearth": "Natural Earth",
    "ourairports": "OurAirports",
    "un": "UN",
    "worldportindex": "World Port Index",
}


# --- Layers -------------------------------------------------------------------

class LayerSpec(NamedTuple):
    """One layer that can be added to a map frame.

    layer   -- layer file name without extension (in 312_Layer_files/3121_arcpro)
    pattern -- dataset file pattern, after the prefix (e.g. "_admn_ad0_py_*_pp*.shp")
    folder  -- subfolder of 2_Active_Data holding the data
    frame   -- map in the template to add it to ("Main map" or "Location map")
    prefix  -- "country" (affected country ISO3), "world" (WORLD_PREFIX) or "region" ("reg")
    exclude_affected_country -- hide the affected country's own features (for
               neighbouring-country layers; the country has its own layers)
    """
    layer: str
    pattern: str
    folder: str
    frame: str
    prefix: str = "country"
    exclude_affected_country: bool = False


MAIN = "Main map"
LOCATION = "Location map"

LAYERS = [
    # Main map
    LayerSpec("admn_ad0_py_all_thematic", "_admn_ad0_py_*_ine_pp*.shp", "202_admn", MAIN),
    LayerSpec("stle_stl_pt_natearth_cap-city", "_stle_stl_pt_*_nat*earth_pp*.shp", "229_stle", MAIN),
    LayerSpec("tran_air_pt_ourairports_lge-med", "_tran_air_pt_*_pp*.shp", "232_tran", MAIN),
    LayerSpec("tran_por_pt_worldports", "_tran_por_pt_*_pp*.shp", "232_tran", MAIN),
    LayerSpec("elev_cst_ln_all", "_elev_cst_ln_*_pp*.shp", "211_elev", MAIN),
    LayerSpec("admn_ad0_ln_all_reference", "_admn_ad0_ln_*_ine_pp*.shp", "202_admn", MAIN),
    LayerSpec("tran_rds_ln_natearth", "_tran_rds_ln_*_nat*earth_pp*.shp", "232_tran", MAIN),
    LayerSpec("tran_rds_ln_natearth_prim-sec", "_tran_rds_ln_*_nat*earth_pp*.shp", "232_tran", MAIN),
    LayerSpec("tran_rrd_ln_all", "_tran_rrd_ln_*_pp*.shp", "232_tran", MAIN),
    LayerSpec("phys_riv_ln_natearth", "_phys_riv_ln_*_nat*earth_pp*.shp", "221_phys", MAIN),
    LayerSpec("phys_lak_py_all", "_phys_lak_py_*_pp*.shp", "221_phys", MAIN),
    LayerSpec("admn_ad1_ln_all_reference", "_admn_ad1_ln_*_ine_pp*.shp", "202_admn", MAIN),
    LayerSpec("admn_ad2_ln_all_reference", "_admn_ad2_ln_*_ine_pp*.shp", "202_admn", MAIN),
    LayerSpec("elev_dem_ras_all", "_elev_dem_ras_*_pp*.tif", "211_elev", MAIN),
    LayerSpec("elev_hsh_ras_all", "_elev_hsh_ras_*_pp*.tif", "211_elev", MAIN),
    LayerSpec("admn_ad1_py_all_reference", "_admn_ad1_py_*_ine_pp*.shp", "202_admn", MAIN),
    LayerSpec("admn_ad2_py_all_reference", "_admn_ad2_py_*_ine_pp*.shp", "202_admn", MAIN),
    LayerSpec("admn_adx_ln_all_reference", "_admn_adx_ln_*_pp*.shp", "202_admn", MAIN,
              prefix="world", exclude_affected_country=True),
    LayerSpec("carto_fea_py_all", "_carto_fea_py_*_pp*.shp", "207_carto", MAIN),
    LayerSpec("admn_adx_py_all_reference", "_admn_adx_py_*_pp*.shp", "202_admn", MAIN, prefix="world"),

    # Location map
    # LayerSpec("carto_fea_py_all", "_carto_fea_py_*_pp*.shp", "207_carto", LOCATION),  # disabled for now
    LayerSpec("elev_cst_ln_all", "_elev_cst_ln_*_pp*.shp", "211_elev", LOCATION),
    LayerSpec("admn_ad1_ln_all_location", "_admn_ad1_ln_*_ine_pp*.shp", "202_admn", LOCATION),
    LayerSpec("admn_adx_ln_all_location", "_admn_adx_ln_*_pp*.shp", "202_admn", LOCATION, prefix="world"),
    LayerSpec("admn_ad0_py_all_location", "_admn_ad0_py_*_ine_pp*.shp", "202_admn", LOCATION),
    LayerSpec("admn_adx_py_all_location", "_admn_adx_py_*_pp*.shp", "202_admn", LOCATION,
              prefix="world", exclude_affected_country=True),
]

# Each map frame is zoomed to the full extent of this layer, then its scale is
# rounded to the nearest 1,000 and multiplied (the Location map shows a wider
# area than the country itself).
FRAME_EXTENTS = {
    MAIN: ("admn_ad0_py_all_thematic", 1),
    LOCATION: ("admn_ad0_py_all_location", 2),
}

# The legend lists every Main map layer except these: background layers, and
# layers whose symbol has no label (or repeats another layer's label).
LEGEND_EXCLUDE = [
    "carto_fea_py_all",
    "elev_dem_ras_all",
    "elev_hsh_ras_all",
    "admn_ad0_py_all_thematic",
    "admn_ad1_py_all_reference",
    "admn_ad2_py_all_reference",
    "admn_adx_py_all_reference",
    "admn_adx_ln_all_reference",
]


# --- Maps ---------------------------------------------------------------------

class MapSpec(NamedTuple):
    """One map product.

    code        -- map code, e.g. "MA901"
    output_name -- used in the output file names: <code>-<version>-<output_name>.aprx/.jpg
    title, summary -- text for the layout's title and summary elements
    layers      -- layer names to add, top of the drawing order first. Each name
                   is added to every map frame that has a LayerSpec for it.
    """
    code: str
    output_name: str
    title: str
    summary: str
    layers: list


# Location map layers shared by every reference map.
_LOCATION_LAYERS = [
    "admn_ad1_ln_all_location",
    "admn_adx_ln_all_location",
    "admn_ad0_py_all_location",
    "admn_adx_py_all_location",
]

MAPS = [
    MapSpec(
        code="MA901",
        output_name="country-overview-with-admin1-and-boundaries",
        title="Country Overview with Admin 1 Boundaries and Topography",
        summary="Country overview with topography displayed",
        layers=[
            "stle_stl_pt_natearth_cap-city",
            "tran_air_pt_ourairports_lge-med",
            "tran_por_pt_worldports",
            "elev_cst_ln_all",
            "admn_ad0_ln_all_reference",
            "admn_ad1_ln_all_reference",
            "phys_riv_ln_natearth",
            "phys_lak_py_all",
            "admn_adx_ln_all_reference",
            "carto_fea_py_all",
            "elev_dem_ras_all",
            "elev_hsh_ras_all",
            "admn_ad1_py_all_reference",
            "admn_ad0_py_all_thematic",
            "admn_adx_py_all_reference",
        ] + _LOCATION_LAYERS,
    ),
    MapSpec(
        code="MA002",
        output_name="country-overview-with-admin1-boundaries",
        title="Country Overview with Admin 1 Boundaries",
        summary="Country overview with detail of Admin 1 boundaries and major cities",
        layers=[
            "stle_stl_pt_natearth_cap-city",
            "tran_air_pt_ourairports_lge-med",
            "tran_por_pt_worldports",
            "elev_cst_ln_all",
            "admn_ad0_ln_all_reference",
            "admn_ad1_ln_all_reference",
            "phys_riv_ln_natearth",
            "phys_lak_py_all",
            "admn_adx_ln_all_reference",
            "carto_fea_py_all",
            "admn_ad1_py_all_reference",
            "admn_ad0_py_all_thematic",
            "admn_adx_py_all_reference",
        ] + _LOCATION_LAYERS,
    ),
    MapSpec(
        code="MA003",
        output_name="country-overview-with-admin2-boundaries-and-cities",
        title="Country Overview with Admin 2 Boundaries",
        summary="Country overview with detail of Admin 2 boundaries and major cities",
        layers=[
            "stle_stl_pt_natearth_cap-city",
            "tran_air_pt_ourairports_lge-med",
            "tran_por_pt_worldports",
            "elev_cst_ln_all",
            "admn_ad0_ln_all_reference",
            "admn_ad1_ln_all_reference",
            "admn_ad2_ln_all_reference",
            "phys_riv_ln_natearth",
            "phys_lak_py_all",
            "admn_adx_ln_all_reference",
            "carto_fea_py_all",
            "admn_ad2_py_all_reference",
            "admn_ad1_py_all_reference",
            "admn_ad0_py_all_thematic",
            "admn_adx_py_all_reference",
        ] + _LOCATION_LAYERS,
    ),
    MapSpec(
        code="MA004",
        output_name="country-overview-with-transport",
        title="Country Overview with Transport",
        summary="Shows country overview with transport information such as airports and ports",
        layers=[
            "stle_stl_pt_natearth_cap-city",
            "tran_air_pt_ourairports_lge-med",
            "tran_por_pt_worldports",
            "elev_cst_ln_all",
            "tran_rds_ln_natearth",
            "admn_ad0_ln_all_reference",
            "admn_ad1_ln_all_reference",
            "admn_ad2_ln_all_reference",
            "phys_riv_ln_natearth",
            "phys_lak_py_all",
            "admn_adx_ln_all_reference",
            "carto_fea_py_all",
            "admn_ad2_py_all_reference",
            "admn_ad1_py_all_reference",
            "admn_ad0_py_all_thematic",
            "admn_adx_py_all_reference",
        ] + _LOCATION_LAYERS,
    ),
]
