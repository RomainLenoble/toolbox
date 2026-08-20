#!/bin/sh
# #SBATCH --job-name interpole_gl
# #SBATCH --qos debug
# #SBATCH --time=0:50:00    # temps reel
# #SBATCH --nodes=2

#
# Template for interpolation of aerosol to target geometry
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

source /home/gmgec/mrgo/lenobler/SAVE/code/GL/config/setenv.belenos
ulimit -s unlimited

GEOM=ALPX3
# PATH to gl
GLPATH=/home/gmgec/mrgo/lenobler/SAVE/code/GL//belenos_cy43/bin

# Climate file for target domain
CLIMATEFILE=/scratch/climat/CEDRE/data/atm/BCOND/${GEOM}CIE/Const.Clim.${GEOM}CIE.01

PATH_CAMS=/scratch/work/lenobler/DATA/ALPX3/restart/CAMS

# FILE_CAMS="CAMS_2012101700.grib"
# FILE_OUTPUT=CAMS_ALPX3_2012101700.grib


# Meteo France 60 levels
NLEV_AROME=60

AHALF_AROME="0.0000, 271.828183, 973.188280, 2030.384267, 3319.226030, 4795.396231, 6433.281895, 8215.601394, 10096.132563, 11988.307779, 13834.682123, 15583.858088, 17187.794886, 18602.008555, 19786.497669, 20706.971826, 21336.176625, 21655.154375, 21654.293789, 21349.398517, 20799.963249, 20063.043810, 19186.977397, 18211.807506, 17170.190348, 16088.493072, 14987.896852, 13885.397395, 12794.651871, 11726.658425, 10690.276989, 9692.612455, 8739.286691, 7834.626887, 6981.796027, 6182.888017, 5439.005999, 4750.338217, 4116.241919, 3535.342466, 3005.652443, 2524.714255, 2089.769666, 1705.297418, 1374.651994, 1093.095953, 855.930809, 658.559613, 496.535186, 365.596754, 261.697342, 181.023925, 120.012010, 75.356071, 44.017046, 23.227928, 10.498339, 3.618836, 0.665238, 0.000000, 0.000000"

BHALF_AROME="0., 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0000000000, 0.0003309675, 0.0017502454, 0.0047467200, 0.0097630763, 0.0172188647, 0.0275061852, 0.0409789128, 0.0579393888, 0.0786244617, 0.1031923737, 0.1317118797, 0.1630387143, 0.1956652968, 0.2291058092, 0.2629653973, 0.2969317553, 0.3307628186, 0.3642733463, 0.3973221613, 0.4298010406, 0.4616256930, 0.4927289008, 0.5230556870, 0.5525602477, 0.5812043462, 0.6089568564, 0.6357941683, 0.6617012022, 0.6866728253, 0.7107155105, 0.7338491181, 0.7561087224, 0.7775464304, 0.7982331608, 0.8182603537, 0.8373613875, 0.8552205742, 0.8718800642, 0.8873812719, 0.9017642034, 0.9150669112, 0.9273250455, 0.9385714693, 0.9488359088, 0.9581446011, 0.9665198957, 0.9739797401, 0.9805369262, 0.9861978406, 0.9909600628, 0.9948065724, 0.9976807303, 1.0000000000"


# Perform the interpolation
OMP_NUM_THREADS=64

NLEV_REF=60

AHALF_CAMS="20, 38.425343, 63.647804, 95.636963, 134.483307, 180.584351, 234.779053, 298.495789, 373.971924, 464.618134, 575.651001, 713.218079, 883.660522, 1094.834717, 1356.474609, 1680.640259, 2082.273926, 2579.888672, 3196.421631, 3960.291504, 4906.708496, 6018.019531, 7306.631348, 8765.053711, 10376.126953, 12077.446289, 13775.325195, 15379.805664, 16819.474609, 18045.183594, 19027.695313, 19755.109375, 20222.205078, 20429.863281, 20384.480469, 20097.402344, 19584.330078, 18864.75, 17961.357422, 16899.46875, 15706.447266, 14411.124023, 13043.21875, 11632.758789, 10209.500977, 8802.356445, 7438.803223, 6144.314941, 4941.77832, 3850.91333, 2887.696533, 2063.779785, 1385.912598, 855.361755, 467.333588, 210.39389, 65.889244, 7.367743, 0, 0"


BHALF_CAMS="0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.000076, 0.000461, 0.001815, 0.005081, 0.011143, 0.020678, 0.034121, 0.05169, 0.073534, 0.099675, 0.130023, 0.164384, 0.202476, 0.243933, 0.288323, 0.335155, 0.383892, 0.433963, 0.484772, 0.53571, 0.586168, 0.635547, 0.683269, 0.728786, 0.771597, 0.811253, 0.847375, 0.879657, 0.907884, 0.93194, 0.951822, 0.967645, 0.979663, 0.98827, 0.994019, 0.99763, 1"



# Time information
#HH=`perl -e "printf('%2.2i', '$TIME')"`
#ORO_FILE=${ORO_FILE-"aer_${DATE}${HH}00+0"}
# ORO_FILE="orography_ALPX3.fa"
ORO_FILE=${PATH_CAMS}/${FILE_CAMS}
ORO_FILE=${FILE_CAMS}

# Link climate file
#
rm -rf climate_aladin
ln -sf $CLIMATEFILE climate_aladin

# Vertical levels on target domain
# AHALF=${AHALF_AROME-$AHALF_CAMS}
# BHALF=${BHALF_AROME-$BHALF_CAMS}
# NLEV=${NLEV_AROME-$NLEV_CAMS}

# Create namelist
#  &NAMINTERP
#   OUTGEO%NLEV=$NLEV_AROME,
#   AHALF=$AHALF_AROME
#   BHALF=$BHALF_AROME
#   atmkey(1:)%shortname = 'aermr01','aermr02','aermr03','aermr04','aermr05','aermr06','aermr07','aermr08','aermr09','aermr10','aermr11','aermr16','aermr17','aermr18'
#   atmkey(1:)%intpm     = 1,1,1,1,1,1,1,1,1,1,1,
#   ATMKEY(1:)%FANAME= 'SEA.SALT1', 'SEA.SALT2', 'SEA.SALT3', 'DES.DUST1', 'DES.DUST2', 'DES.DUST3', 'ORG.MAT1', 'ORG.MAT2', 'BLACK.CAR1', 'BLACK.CAR2', 'SULPHATE', 'NITRATE1', 'NITRATE2', 'AMMONIUM',
#   ORDER=1,
#   NE2EALG=2,
#   LATMKEY_ONLY=T,
#   EXT_BD_ORO = T
#   EXT_BD_ORO_FILE='$ORO_FILE',

cat > naminterp << EOF
&NAMINTERP
  OUTGEO%NLEV=$NLEV_AROME,
  AHALF=$AHALF_AROME
  BHALF=$BHALF_AROME
  atmkey(1:)%shortname = 'aermr01','aermr02','aermr03','aermr04','aermr05','aermr06','aermr07','aermr08','aermr09','aermr10','aermr11','aermr16','aermr17','aermr18',
  atmkey(1:)%intpm     = 1,1,1,1,1,1,1,1,1,1,1,1,1,1
  ORDER=1 ! order interpolation, attention larger boundary if order increase
  NE2EALG=2,
  LATMKEY_ONLY=T,
  EXT_BD_ORO = T
  EXT_BD_ORO_FILE='$ORO_FILE',
  limap(1)%faname='N_CCN_F1'
  limap(1)%use_shortname='aermr01','aermr02','aermr03'
  limap(1)%rho=2160.,       ! density kg/m3
  limap(1)%md=0.8,          ! Diametre en m
  limap(1)%sigma=1.89,      ! Sigma lognormale ?
  limap(2)%faname='N_CCN_F2'
  limap(2)%use_shortname='aermr11'
  limap(2)%rho=2000.,
  limap(2)%md=0.5,
  limap(2)%sigma=1.6,
  limap(3)%faname='N_CCN_F3'
  limap(3)%use_shortname='aermr07','aermr09'
  limap(3)%rho=1750.,
  limap(3)%md=0.2,
  limap(3)%sigma=1.6,
  limap(4)%faname='N_IFN_F1'
  limap(4)%use_shortname='aermr04','aermr05','aermr06'
  limap(4)%rho=2300.,
  limap(4)%md=0.8,
  limap(4)%sigma=1.9,
  limap(5)%faname='N_IFN_F2'
  limap(5)%use_shortname='aermr08','aermr10'
  limap(5)%rho=1700.,
  limap(5)%md=0.2,
  limap(5)%sigma=1.6,
  lmap2lima = T,
  printlev = 2,
/
EOF

  # limap(2)%faname='N_CCN_F1'
  # limap(2)%use_shortname='aermr01','aermr02','aermr03'
  # limap(2)%rho=2160.,
  # limap(2)%md=0.8,
  # limap(2)%sigma=1.89,
  # limap(1)%faname='N_CCN_F2'
  # limap(1)%use_shortname='aermr11','aermr16','aermr17','aermr18'
  # limap(1)%rho=2000.,
  # limap(1)%md=0.5,
  # limap(1)%sigma=1.6,
  # limap(3)%faname='N_CCN_F3'
  # limap(3)%use_shortname='aermr07','aermr09'
  # limap(3)%rho=1750.,
  # limap(3)%md=0.2,
  # limap(3)%sigma=1.6,
  # limap(4)%faname='N_IFN_F1'
  # limap(4)%use_shortname='aermr04','aermr05','aermr06'
  # limap(4)%rho=2300.,
  # limap(4)%md=0.8,
  # limap(4)%sigma=1.9,
  # limap(5)%faname='N_IFN_F2'
  # limap(5)%use_shortname='aermr08','aermr10'
  # limap(5)%rho=1700.,
  # limap(5)%md=0.2,
  # limap(5)%sigma=1.6,
  # lmap2lima = T,
  # printlev = 0,

# cat naminterp

#$GLPATH//gl -lbc ifs -n naminterp aer_FRANMG_${DATE}${HH}00+$STEP -o aer_${DATE}${HH}00+$STEP.fa
# cp /scratch/work/lenobler/DATA/CAMS/aer_ALPX3_121021000012.grib ficAER


$GLPATH//gl -lbc ifs -n naminterp ficAER -o ficOUT
