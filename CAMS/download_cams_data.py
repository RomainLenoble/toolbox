#!/usr/bin/env python3
"""
Download CAMS global reanalysis (EAC4) aerosol data from the Copernicus
Climate Data Store (CDS), based on the requests used in cdsapi.ipynb.

Requirements
------------
pip install cdsapi

You also need a CDS API key configured, either in ~/.cdsapirc:

    url: https://ads.atmosphere.copernicus.eu/api
    key: <your-personal-access-token>

or via the CDSAPI_URL / CDSAPI_KEY environment variables.
Get your key at: https://ads.atmosphere.copernicus.eu/how-to-api

Usage
-----
Edit the CONFIG section below (dates, times, variables, area, output dir),
then run:

    python download_cams_data.py

By default this downloads PRESSURE-level data (a few selected levels plus
the 2D aerosol-related fields), one GRIB file per date and time. The
model-level call in main() is commented out; swap the two if you need it.
"""

import os
import time
import logging

import cdsapi

# --------------------------------------------------------------------------
# CONFIG - edit these to match what you need
# --------------------------------------------------------------------------

DATASET = "cams-global-reanalysis-eac4"

OUTPUT_DIR = ".//ec/res4/hpcperm/fra6549/data/CAMS_data/Hymex/"
OUTPUT_DIR = "Hymex/"

AREA = [56, -12.9, 35, 24]  # [North, West, South, East]

AEROSOL_VARIABLES = [
    "dust_aerosol_0.03-0.55um_mixing_ratio",
    "dust_aerosol_0.55-0.9um_mixing_ratio",
    "dust_aerosol_0.9-20um_mixing_ratio",
    "hydrophilic_black_carbon_aerosol_mixing_ratio",
    "hydrophilic_organic_matter_aerosol_mixing_ratio",
    "hydrophobic_black_carbon_aerosol_mixing_ratio",
    "hydrophobic_organic_matter_aerosol_mixing_ratio",
    "sea_salt_aerosol_0.03-0.5um_mixing_ratio",
    "sea_salt_aerosol_0.5-5um_mixing_ratio",
    "sea_salt_aerosol_5-20um_mixing_ratio",
    "sulphate_aerosol_mixing_ratio",
]

# Extra (non-aerosol) fields useful for post-processing, e.g. converting
# mixing ratios to concentrations or computing geopotential height.
# Only added to the model-level request below.
EXTRA_MODEL_LEVEL_VARIABLES = [
    "2m_temperature",
    "surface_geopotential",
    "surface_pressure",
    "specific_humidity",
    "temperature",
]

MODEL_LEVELS = [str(i) for i in range(1, 61)]  # levels 1-60

# Pressure levels (hPa) kept for aerosol studies: the boundary layer and lower
# troposphere where most aerosol mass sits (1000/925/850), the typical
# long-range dust/smoke transport layer (700) and the mid-troposphere (500).
# The full list of levels offered by EAC4 is:
#   1, 2, 3, 5, 7, 10, 20, 30, 50, 70, 100, 150, 200, 250, 300, 400, 500,
#   600, 700, 800, 850, 900, 925, 950, 1000
PRESSURE_LEVELS = ["1000", "925", "850", "700", "500"]

# Fields on pressure levels needed with the mixing ratios, e.g. to convert
# them to mass concentrations (air density = p / (R T)).
EXTRA_PRESSURE_LEVEL_VARIABLES = [
    "temperature",
    "specific_humidity",
]

# 2D (single-level) fields relevant for aerosol studies. They have no level
# dimension, so CDS returns them in the same request as the pressure-level
# variables (same mixing of single-level and multi-level variables as the
# model-level request already does with 2m_temperature, surface_pressure...).
AEROSOL_2D_VARIABLES = [
    # surface particulate matter, to compare with air-quality stations
    # "particulate_matter_1um",
    # "particulate_matter_2.5um",
    # "particulate_matter_10um",
    # aerosol optical depth at 550 nm: total and per species
    "total_aerosol_optical_depth_550nm",
    "dust_aerosol_optical_depth_550nm",
    "sea_salt_aerosol_optical_depth_550nm",
    "sulphate_aerosol_optical_depth_550nm",
    "black_carbon_aerosol_optical_depth_550nm",
    "organic_matter_aerosol_optical_depth_550nm",
    # meteorological drivers of emission, mixing and removal
    "boundary_layer_height",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "total_cloud_cover",
    "mean_sea_level_pressure",
    "surface_pressure",
    "2m_temperature",
]

# Uniform date handling: always an explicit list of "YYYY-MM-DD" strings,
# used the same way for both model-level and pressure-level requests
# (one request/file per date). Build it however is convenient, e.g. with
# pandas.date_range(...).strftime("%Y-%m-%d").tolist().
from datetime import date, timedelta
def make_date_list(start, end, step=1):
    """Return a list of 'YYYY-MM-DD' strings from start to end (inclusive)."""
    d0 = date.fromisoformat(start)
    d1 = date.fromisoformat(end)
    return [(d0 + timedelta(days=i)).isoformat()
            for i in range(0, (d1 - d0).days + 1, step)]

DATE_LIST = make_date_list("2020-09-15", "2020-10-15")
DATE_LIST = make_date_list("2012-09-02", "2012-11-01")

# DATE_LIST = [
#     "2012-10-17",
#     "2012-10-18",
#     "2012-10-19",
#     "2012-10-20",
#     "2012-10-21",
#     # "2020-01-01",
#     # "2020-01-02",
# ]

TIME_LIST = [
    "00:00", "03:00", "06:00", "09:00",
    "12:00", "15:00", "18:00", "21:00",
]

RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 30

# --------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def retrieve_with_retry(client, dataset, request, target):
    """Call client.retrieve with a few retries, since CDS requests can
    time out or fail transiently while queued."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            client.retrieve(dataset, request, target=target)
            return
        except Exception as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, RETRY_ATTEMPTS, target, exc)
            if attempt == RETRY_ATTEMPTS:
                raise
            time.sleep(RETRY_WAIT_SECONDS)


def download_cams_data(output_dir, level_type, levels, variables, dates, times, area):
    """Download CAMS EAC4 data, one GRIB file per date.

    level_type : "model" or "pressure" - selects the "model_level" or
                 "pressure_level" request key, and is used in filenames.
    levels     : list of level strings (e.g. MODEL_LEVELS or PRESSURE_LEVELS)
    variables  : list of CDS variable names to request together
    dates      : list of "YYYY-MM-DD" strings, one request/file per date
    times      : list of "HH:MM" strings
    area       : [North, West, South, East]
    """
    assert level_type in ("model", "pressure")
    level_key = "model_level" if level_type == "model" else "pressure_level"

    os.makedirs(output_dir, exist_ok=True)
    client = cdsapi.Client()

    for date in dates:
        for time in times:
            request = {
                level_key: levels,
                "date": [date],
                "time": time,
                "data_format": "grib",
                "variable": variables,
                "area": area,
            }
            target = os.path.join(output_dir, f"CAMS_{level_type}_level_{date}_{time}.grib")
            print(request, target)
            if os.path.exists(target):
                log.info("Skipping %s (already exists)", target)
                continue
            log.info("Requesting %s-level data for %s -> %s", level_type, date, target)
            retrieve_with_retry(client, DATASET, request, target)


def main():
    download_cams_data(
        output_dir=os.path.join(OUTPUT_DIR, "pressure_level"),
        level_type="pressure",
        levels=PRESSURE_LEVELS,
        variables=AEROSOL_VARIABLES + EXTRA_PRESSURE_LEVEL_VARIABLES + AEROSOL_2D_VARIABLES,
        dates=DATE_LIST,
        times=TIME_LIST,
        area=AREA,
    )

    # download_cams_data(
    #     output_dir=os.path.join(OUTPUT_DIR, "model_level"),
    #     level_type="model",
    #     levels=MODEL_LEVELS,
    #     variables=AEROSOL_VARIABLES + EXTRA_MODEL_LEVEL_VARIABLES,
    #     dates=DATE_LIST,
    #     times=TIME_LIST,
    #     area=AREA,
    # )

    log.info("Done. Files saved under %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()