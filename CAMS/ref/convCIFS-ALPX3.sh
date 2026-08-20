#!/bin/bash
#SBATCH -p normal256
#SBATCH -n 1
#SBATCH -c 1
#SBATCH -N 1
#SBATCH -t 00:15:00
#SBATCH --job-name=conv_MACC_LIMA

chemin=${HOME}/SAVE/EPYGRAM_dev
cd ${HOME}
. .bash_profile
exp='ALPX3'
YY=`expr $1 | cut -c1-4`  # year
MM=`expr $1 | cut -c5-6`  # Month
DD=`expr $1 | cut -c7-8`  # Day
HH=`expr $1 | cut -c9-10` # Hour
DOM=$2                    # Domain
CAMS_OPT=$3               # Option CANS
reptmp=$4                 # Temperorary repo
res=$HH                    # resolution horraire 

if [ ${HH} == '00' ] ; then
res=`expr $1 | cut -c10`
fi 
Z=`date --date="$YY-$MM-$DD $HH:00:00" "+%s"`

# Load environnement
source $HOME/gl/config/setenv.belenos

cd $reptmp
echo REPTMP $reptmp
pwd
chmod +w *

cp $HOME/gl/scr/orog_file_${DOM} orog_file_${DOM}
cp $HOME/gl/scr/Aerosol_main_LIMA_${DOM}_${CAMS_OPT} Aerosol_main_LIMA_${DOM}_${CAMS_OPT}
cp $HOME/gl/scr/Aer_interpol_LIMA_${DOM}_${CAMS_OPT} Aer_interpol_LIMA_${DOM}_${CAMS_OPT}

for ech in 0 3 6 9 12 15 18 21 24 27 30 33 36 39 42 45 48
do

if [ ${ech} -lt 10 ]; then
  iech=0${ech}
else
  iech=${ech}
fi

STEP=$((3600*$ech))
W=`expr $Z + $STEP`
X=`date --date=@"$W" "+%Y%m%d%H%M%S"`
YY1=`expr $X | cut -c1-4`
MM1=`expr $X | cut -c5-6`
DD1=`expr $X | cut -c7-8`
ECHDAY=`expr $X | cut -c9-10`
if [ $ECHDAY -lt 10 ]; then
  ECHDAY=`expr $X | cut -c10`
fi

echo ${YY}${MM}${DD} ${YY1}${MM1}${DD1} $ECHDAY
echo $WORKDIR/DATA/CAMS/aer_${DOM}_${YY1}${MM1}${DD1}0000+${ECHDAY}
cp -f $WORKDIR/DATA/CAMS/aer_${DOM}_${YY1}${MM1}${DD1}0000+${ECHDAY} ficAER
cp -f ${HOME}/DATAS_xp/clim/${DOM}_m01 climate_aladin
#cp -f /scratch/mtool/antoines/cache/vortex/arome/FOG1250/7KAN/${YY}${MM}${DD}T${HH}00P/coupling/cpl.arome.fog1250-1250m000+00${iech}:00.fa ficOUT
cp -f BOUNDARY+00${iech}:00 ficOUT

ls -lrt

./Aerosol_main_LIMA_${DOM}_${CAMS_OPT}
mv -f ficOUT CPLOUT+00${iech}:00

rm -f ficAER
done
