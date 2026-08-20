#!/usr/bin/env python3
import os
import sys
import subprocess
import textwrap
import numpy as np

# 'aermr01', 'Sea Salt Aerosol (0.03 - 0.5 um) Mixing Ratio',
# 'aermr02', 'Sea Salt Aerosol (0.5 - 5 um) Mixing Ratio',
# 'aermr03', 'Sea Salt Aerosol (5 - 20 um) Mixing Ratio',
# 'aermr04',: 'Dust Aerosol (0.03 - 0.55 um) Mixing Ratio',
# 'aermr05', 'Dust Aerosol (0.55 - 0.9 um) Mixing Ratio',
# 'aermr06', 'Dust Aerosol (0.9 - 20 um) Mixing Ratio',
# 'aermr07', 'Hydrophilic Organic Matter Aerosol Mixing Ratio',
# 'aermr08', 'Hydrophobic Organic Matter Aerosol Mixing Ratio',
# 'aermr09', 'Hydrophilic Black Carbon Aerosol Mixing Ratio',
# 'aermr10', 'Hydrophobic Black Carbon Aerosol Mixing Ratio',
# 'aermr11', 'Sulphate Aerosol Mixing Ratio',

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <ficAER> <ficOUT>")
        sys.exit(1)

    fic_aer, fic_out = sys.argv[1], sys.argv[2]

    # Environment setup
    os.environ["ULIMIT"] = "unlimited"  # mimic ulimit -s unlimited

    # Paths
    GLPATH = "/home/gmgec/mrgo/lenobler/SAVE/code/GL//belenos_cy43/bin"
    GEOM = "ALPX3"
    CLIMATEFILE = f"/scratch/climat/CEDRE/data/atm/BCOND/{GEOM}CIE/Const.Clim.{GEOM}CIE.01"

    # Levels
    NLEV_AROME = 60

    AHALF_AROME = (
        "0.0000, 271.828183, 973.188280, 2030.384267, 3319.226030, 4795.396231, "
        "6433.281895, 8215.601394, 10096.132563, 11988.307779, 13834.682123, "
        "15583.858088, 17187.794886, 18602.008555, 19786.497669, 20706.971826, "
        "21336.176625, 21655.154375, 21654.293789, 21349.398517, 20799.963249, "
        "20063.043810, 19186.977397, 18211.807506, 17170.190348, 16088.493072, "
        "14987.896852, 13885.397395, 12794.651871, 11726.658425, 10690.276989, "
        "9692.612455, 8739.286691, 7834.626887, 6981.796027, 6182.888017, "
        "5439.005999, 4750.338217, 4116.241919, 3535.342466, 3005.652443, "
        "2524.714255, 2089.769666, 1705.297418, 1374.651994, 1093.095953, "
        "855.930809, 658.559613, 496.535186, 365.596754, 261.697342, "
        "181.023925, 120.012010, 75.356071, 44.017046, 23.227928, 10.498339, "
        "3.618836, 0.665238, 0.000000, 0.000000"
    )

    BHALF_AROME = (
        "0., 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, "
        "0.0000000000, 0.0000000000, 0.0000000000, 0.0003309675, 0.0017502454, "
        "0.0047467200, 0.0097630763, 0.0172188647, 0.0275061852, 0.0409789128, "
        "0.0579393888, 0.0786244617, 0.1031923737, 0.1317118797, 0.1630387143, "
        "0.1956652968, 0.2291058092, 0.2629653973, 0.2969317553, 0.3307628186, "
        "0.3642733463, 0.3973221613, 0.4298010406, 0.4616256930, 0.4927289008, "
        "0.5230556870, 0.5525602477, 0.5812043462, 0.6089568564, 0.6357941683, "
        "0.6617012022, 0.6866728253, 0.7107155105, 0.7338491181, 0.7561087224, "
        "0.7775464304, 0.7982331608, 0.8182603537, 0.8373613875, 0.8552205742, "
        "0.8718800642, 0.8873812719, 0.9017642034, 0.9150669112, 0.9273250455, "
        "0.9385714693, 0.9488359088, 0.9581446011, 0.9665198957, 0.9739797401, "
        "0.9805369262, 0.9861978406, 0.9909600628, 0.9948065724, 0.9976807303, "
        "1.0000000000"
    )

    # Climate file symlink
    if os.path.islink("climate_aladin") or os.path.exists("climate_aladin"):
        os.remove("climate_aladin")
    os.symlink(CLIMATEFILE, "climate_aladin")


    # From Bozzo et al., 2020
    RCCN = [0.085e-6, 1.2e-6, 6.0e-6, 0.0355e-6, 0.0212e-6, 0.0118e-6]
    LOGSIGCCN = [0.69, 0.69, 0.69, 0.69, 0.81, 0.69]
    RHOCCN = [1183, 1183, 1183, 1760, 1800, 1000]

    # Dust and hydrophobic particles
    XMDIAM_IFN = [0.163e-6, 0.67e-6, 3.3e-6, 0.0212e-6, 0.0118e-6]
    XSIGMA_IFN = [2.0, 2.0, 2.0, 2.24, 2.0]
    XRHO_IFN = [2610, 2610, 2610, 1800, 1000]

        
    # CCN particles
    CCN = {
        "faname": ["SEASALT1", "SEASALT2", "SEASALT3", "SULF", "OM1", "BC1"],
        "shortname": ["aermr01", "aermr02", "aermr03", "aermr11", "aermr07", "aermr09"],
        "md":     np.array(RCCN)*2*1e6,
        "sigma":  np.exp(LOGSIGCCN),
        "rho":    RHOCCN,
    }

    # IFN particles (Dust + hydrophobic OM/BC)
    IFN = {
        "faname": ["DUST1", "DUST2", "DUST3", "OM2", "BC2"],
        'shortname': ["aermr04", "aermr05", "aermr06", "aermr08", "aermr10"],
        "md":     np.array(XMDIAM_IFN)*1e6,
        "sigma":  XSIGMA_IFN,
        "rho":    XRHO_IFN,
    }



    # limap entry: 
        # rho : density, kg/m**3
        # md : Diametre en micro m
        # sigma : sigma loi log normale 

    # Combine CCN and IFN into a list of entries
    all_particles = []

    for name, short, md, sigma, rho in zip(
        CCN["faname"], CCN["shortname"], CCN["md"], CCN["sigma"], CCN["rho"]
    ):
        all_particles.append({
            "faname": name,
            "use_shortname": [short],
            "md": md,
            "sigma": sigma,
            "rho": rho
        })

    for name, short, md, sigma, rho in zip(
        IFN["faname"], IFN["shortname"], IFN["md"], IFN["sigma"], IFN["rho"]
    ):
        all_particles.append({
            "faname": name,
            "use_shortname": [short],
            "md": md,
            "sigma": sigma,
            "rho": rho
        })
    # Build limap section
    limap_lines = []
    for i, entry in enumerate(all_particles, start=1):
        use_short = ",".join(f"'{s}'" for s in entry["use_shortname"])
        block = textwrap.indent(textwrap.dedent(f"""\
            limap({i})%faname='{entry["faname"]}',
            limap({i})%use_shortname={use_short},
            limap({i})%rho={entry["rho"]},
            limap({i})%md={entry["md"]},
            limap({i})%sigma={entry["sigma"]},
        """), "  ")
        limap_lines.append(block)

    limap_content = "".join(limap_lines)

    # Final namelist content with correct indentation
    namelist_content = f"""&NAMINTERP
  OUTGEO%NLEV={NLEV_AROME},
  AHALF={AHALF_AROME}
  BHALF={BHALF_AROME}
  atmkey(1:)%shortname = 'aermr01','aermr02','aermr03','aermr04','aermr05','aermr06','aermr07','aermr08','aermr09','aermr10','aermr11',
  atmkey(1:)%intpm     = 1,1,1,1,1,1,1,1,1,1,1,
  ORDER=1
  NE2EALG=2,
  LATMKEY_ONLY=T,
  lmap2lima = T,
  printlev = 2,
{limap_content}
/
"""
    


    with open("naminterp", "w") as f:
        f.write(namelist_content)

    # Run gl
    cmd = [os.path.join(GLPATH, "gl"), "-lbc", "ifs", "-n", "naminterp", fic_aer, "-o", fic_out]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
