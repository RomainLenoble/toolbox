#!/home/gmgec/mrgo/lenobler/miniforge3/bin/python3
import os
import re
from datetime import datetime, timedelta
import numpy as np
import epygram
from multiprocessing import Pool, cpu_count
import argparse
from functools import partial

from lbc_config import load_config

epygram.init_env()  # required

# -------------------------------------------------------
# Parse timestamp from file like: CAMS_AROME_20121017.0300
# -------------------------------------------------------
def parse_timestamp(fname):
    m = re.search(r"(\d{8})\.(\d{4})", fname)
    if not m:
        return None
    date, time = m.groups()
    return datetime.strptime(date + time, "%Y%m%d%H%M")


# -------------------------------------------------------
# Interpolate two EPyGrAM resources (file1 → file2)
# -------------------------------------------------------
def interpolate_resources(res1, res2, alpha):
    """
    Linear interpolation:
      field_new = (1 - alpha) * field1 + alpha * field2
    """
    newfields = {}

    # Loop on all fields in the first file
    for key in res1.listfields():
        f1 = res1.readfield(key)

        # Read same field from second file
        f2 = res2.readfield(key)

        # Interpolate values
        fnew = f1.copy()                      # keep geometry + headers
        fnew.setdata((1 - alpha) * f1.getdata() + alpha * f2.getdata())

        newfields[key] = fnew

    return newfields


# -------------------------------------------------------
# Write a new GRIB file using template metadata
# -------------------------------------------------------
def write_grib_from_fields(template_path, fields_dict, new_time, outpath):
    template = epygram.formats.resource(template_path, "r")

    # Copy the template resource but write new fields
    out = epygram.formats.resource(outpath, "w",
                                 fmt=template.format,
                                 compression=None)

    for key, field in fields_dict.items():
        # Update date/time in each field's header
        field.validity.set(date_time=new_time)
        out.writefield(field)

    out.close()
    template.close()



# ---------------------------------------------------
# Function to process a single file pair
# ---------------------------------------------------
def process_file_pair(i, input_folder, files, output_folder, outname_prefix):
    f1 = files[i]
    f2 = files[i + 1]

    t1 = parse_timestamp(f1)
    t2 = parse_timestamp(f2)

    path1 = os.path.join(input_folder, f1)
    path2 = os.path.join(input_folder, f2)

    print(f"Processing: {f1} → {f2}")

    # Open GRIB resources
    r1 = epygram.formats.resource(path1, "r")
    r2 = epygram.formats.resource(path2, "r")

    # Number of hours between files
    hours = int((t2 - t1).total_seconds() / 3600)

    # Interpolate missing hours
    if hours > 1:
        for h in range(1, hours):
            t_new = t1 + timedelta(hours=h)
            alpha = h / hours

            fields_interp = interpolate_resources(r1, r2, alpha)

            outname = f"{outname_prefix}{t_new:%Y%m%d.%H%M}"
            write_grib_from_fields(
                path1, fields_interp, t_new,
                os.path.join(output_folder, outname)
            )

    r1.close()
    r2.close()


def main():
    parser = argparse.ArgumentParser(description="Interpolate CAMS files to the target Arome domain")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the input folder containing CAMS files")
    parser.add_argument("--output_folder", type=str, help="Path to the output folder where results will be saved")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML config file (see config/ALPX3.yaml)")
    args = parser.parse_args()

    config = load_config(args.config)

    input_folder = args.input_folder
    output_folder = args.output_folder if args.output_folder is not None else args.input_folder
    os.makedirs(output_folder, exist_ok=True)


    files = sorted(
        [f for f in os.listdir(input_folder) if re.search(r"\d{8}\.\d{4}", f)],
        key=parse_timestamp
    )


    # ---------------------------------------------------
    # Parallel execution
    # ---------------------------------------------------
    NPROC = config["runtime"]["nproc_time_interp"]
    outname_prefix = config["naming"]["cams_interp_prefix"]
    partial_func = partial(
        process_file_pair, input_folder=input_folder, output_folder=output_folder,
        files=files, outname_prefix=outname_prefix,
    )

    with Pool(NPROC) as pool:
        pool.map(partial_func, range(len(files)-1))
        
if __name__ == "__main__":
    main()
        
# for i in range(len(files) - 1):
#     f1 = files[i]
#     f2 = files[i + 1]

#     t1 = parse_timestamp(f1)
#     t2 = parse_timestamp(f2)

#     path1 = os.path.join(indir, f1)
#     path2 = os.path.join(indir, f2)

#     print(f"Processing: {f1} → {f2}")

#     # Open both GRIB resources
#     r1 = epygram.formats.resource(path1, "r")
#     r2 = epygram.formats.resource(path2, "r")

#     # # Write the first file as-is, but normalized timestamp
#     # outname = f"{t1:%Y%m%d.%H%M}"
#     # fields_original = {k: r1.readfield(k) for k in r1.listfields()}
#     # write_grib_from_fields(path1, fields_original, t1,
#     #                        os.path.join(outdir, outname))

#     # Compute number of hours between files
#     hours = int((t2 - t1).total_seconds() / 3600)

#     # Interpolate missing hours
#     if hours > 1:
#         for h in range(1, hours):
#             t_new = t1 + timedelta(hours=h)
#             alpha = h / hours

#             fields_interp = interpolate_resources(r1, r2, alpha)

#             outname = f"CAMS_AROME_{t_new:%Y%m%d.%H%M}"
#             write_grib_from_fields(
#                 path1, fields_interp, t_new,
#                 os.path.join(outdir, outname)
#             )

#     r1.close()
#     r2.close()
