#!/bin/bash

#SBATCH --job-name=get_era5_IOP_14
#SBATCH --time=14:00:00

START_DATE=20121017
END_DATE=20121020

current=${START_DATE}

# param=133/130/138/152/131/132/134/156/235/172/129,

while [[ ${current} -le ${END_DATE} ]]; do

  for hour in $(seq -w 0 23); do

    mars << EOF
retrieve,
    class=ea,
    AREA=  8.5/-10.3/ -8.2/ 10.5,ROTATION=-43.8/  4.8,
    dataset=era5,
    expver=1,
    stream=oper,
    type=an,
    levtype=ml,
    levelist=1/to/137,
    param=130/138/152/133/152/131/132/129
    date=${current},
    time=${hour}:00:00,
    target="/ec/res4/hpcperm/fra6549/data/03_IOP_14/era5_${current}_${hour}.grib",
    GRID=0.1/0.1
EOF

  done

  current=$(date -d "${current} +1 day" +%Y%m%d)

done
