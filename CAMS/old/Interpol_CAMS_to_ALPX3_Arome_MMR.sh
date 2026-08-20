#!/bin/sh
# #SBATCH --job-name interpole_gl
# #SBATCH --qos debug
# #SBATCH --time=0:50:00    # temps reel
# #SBATCH --nodes=2

#
# Template for interpolation of aerosol to target geometry in MMR
# 
# Ulf Andrae, SMHI, 2021
#
# Remove EXT_BD_ORO* from namelist if orografy is present in each input file
# Convert ficAer and write ficout

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


# Usage: ./interpole_gl.sh ficAER ficOUT

if [ $# -ne 2 ]; then
  echo "Usage: $0 <ficAER> <ficOUT>"
  exit 1
fi

FIC_AER=$1
FIC_OUT=$2

source /home/gmgec/mrgo/lenobler/SAVE/code/GL/config/setenv.belenos
ulimit -s unlimited

# PATH to gl
GLPATH=/home/gmgec/mrgo/lenobler/SAVE/code/GL//belenos_cy43/bin

# Climate file for target domain
GEOM=ALPX3
CLIMATEFILE=/scratch/climat/CEDRE/data/atm/BCOND/${GEOM}CIE/Const.Clim.${GEOM}CIE.01

# Meteo France 60 levels
NLEV_AROME=60

AHALF_AROME="0.0000, 271.828183, 973.188280, 2030.384267, 3319.226030, 4795.396231, 6433.281895, 8215.601394, 10096.132563, 11988.307779, 13834.682123, 15583.858088, 17187.794886, 18602.008555, 19786.497669, 20706.971826, 21336.176625, 21655.154375, 21654.293789, 21349.398517, 20799.963249, 20063.043810, 19186.977397, 18211.807506, 17170.190348, 16088.493072, 14987.896852, 13885.397395, 12794.651871, 11726.658425, 10690.276989, 9692.612455, 8739.286691, 7834.626887, 6981.796027, 6182.888017, 5439.005999, 4750.338217, 4116.241919, 3535.342466, 3005.652443, 2524.714255, 2089.769666, 1705.297418, 1374.651994, 1093.095953, 855.930809, 658.559613, 496.535186, 365.596754, 261.697342, 181.023925, 120.012010, 75.356071, 44.017046, 23.227928, 10.498339, 3.618836, 0.665238, 0.000000, 0.000000"

BHALF_AROME="0., 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0003309675, 0.0017502454, 0.0047467200, 0.0097630763, 0.0172188647, 0.0275061852, 0.0409789128, 0.0579393888, 0.0786244617, 0.1031923737, 0.1317118797, 0.1630387143, 0.1956652968, 0.2291058092, 0.2629653973, 0.2969317553, 0.3307628186, 0.3642733463, 0.3973221613, 0.4298010406, 0.4616256930, 0.4927289008, 0.5230556870, 0.5525602477, 0.5812043462, 0.6089568564, 0.6357941683, 0.6617012022, 0.6866728253, 0.7107155105, 0.7338491181, 0.7561087224, 0.7775464304, 0.7982331608, 0.8182603537, 0.8373613875, 0.8552205742, 0.8718800642, 0.8873812719, 0.9017642034, 0.9150669112, 0.9273250455, 0.9385714693, 0.9488359088, 0.9581446011, 0.9665198957, 0.9739797401, 0.9805369262, 0.9861978406, 0.9909600628, 0.9948065724, 0.9976807303, 1.0000000000"


# Perform the interpolation
OMP_NUM_THREADS=64


# Link climate file
#
rm -rf climate_aladin
ln -sf $CLIMATEFILE climate_aladin


cat > naminterp << EOF
&NAMINTERP
  OUTGEO%NLEV=$NLEV_AROME,
  AHALF=$AHALF_AROME
  BHALF=$BHALF_AROME
  atmkey(1:)%shortname = 'aermr01','aermr02','aermr03','aermr04','aermr05','aermr06','aermr07','aermr08','aermr09','aermr10','aermr11',
  atmkey(1:)%intpm     = 1,1,1,1,1,1,1,1,1,1,1,
  atmkey(1:)%faname    ='SEASALT1','SEASALT2','SEASALT3','DUST1','DUST2','DUST3','OM1','OM2','BC1','BC2','SULF',
  ORDER=1 ! order interpolation, attention larger boundary if order increase
  NE2EALG=2,
  LATMKEY_ONLY=T,
  printlev = 0,
/
EOF


$GLPATH/gl -lbc ifs -n naminterp "$FIC_AER" -o "$FIC_OUT"
