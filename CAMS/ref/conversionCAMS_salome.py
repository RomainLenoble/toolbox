#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import epygram
import numpy as np
import warnings
warnings.filterwarnings('ignore')
import sys
epygram.init_env()

# yyyy = sys.argv[1]
# mm   = sys.argv[2]
# dd   = sys.argv[3]
# rr   = sys.argv[4]
# ccnc = sys.argv[5]
# ech  = sys.argv[6]

yyyy = "2020"
mm   = "02"
dd   = "22"
rr   = "00"
ccnc = "MACC"
ech = "01"
### ==
NBLEV = 156

print("### ======================================== ###")
print("        Conversion CAMS ",yyyy,mm,dd,rr,ccnc)
print("### ======================================== ###")

### PATH
path = "/cnrm/phynh/users/antoines/NO_SAVE/CAMS/"+ccnc+"/"+yyyy+mm+dd+rr+"/"
path_CAMS = "/home/antoines/WorkDir/CAMS/DATAS/"

for ech in ["3","6","9","12","15","18","21","24","27","30","33","36","0"]:
    ### NOM DU FICHIER AVEC LES AEROSOLS
    CAMS = path_CAMS + "ELSCFCAMSFOG500+"+ech+"_"+yyyy+mm+dd+rr
    ### ==
    ### NOM DU FICHIER DANS LEQUEL ECRIRE APRES LA CONVERSION
    if int(ech)<10:
        CPL  = path + "cpl.arome.fog500-500m000+000"+ech+":00.fa"
    else:
        CPL  = path + "cpl.arome.fog500-500m000+00"+ech+":00.fa"
    ### ==
    ###CORESPONDANCE VARIABLES LIMA -- MACC
    limap = [{"faname":"N_CCN_F1", "rho":2160., "md":0.8, "sigma":1.89},
             {"faname":"N_CCN_F2", "rho":2000., "md":0.5, "sigma":1.60},
             {"faname":"N_CCN_F3", "rho":1750., "md":0.2, "sigma":1.60},
             {"faname":"N_IFN_F1", "rho":2300., "md":0.8, "sigma":1.90},
             {"faname":"N_IFN_F2", "rho":1700., "md":0.2, "sigma":1.60}]
    ### ==
    ### DAPRES BENOIT COMMUNEMENT CEST 
    ### CCNF1 = SEA SALT
    ### CCNF2 = SNA
    ### AVEC LES SEA SALT PLUS GROS QUE LES SNA
    
    ### FACTEUR DE MASSE LIMA
    for x in limap:
        x["mass_lima"] = x["rho"]*4.0/3.0*np.pi*((x["md"]*1e-6/2.0)**3)*(np.exp(9.0/2.0*np.log(x["sigma"])**2)) 
    ### ==
    ### BLOUCLE SUR LES NIVEAUX
    for l in range(1,NBLEV+1):
        iLev = str(l)
        while len(iLev) < 3:
            iLev = "0" + iLev
        ### ==
        ### LECTURE FICHIER AEROSOLS
        FA_CAMS = epygram.formats.resource(CAMS, 'r')
        SAEROSOLMR01 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.01')
        SAEROSOLMR02 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.02')
        SAEROSOLMR03 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.03')
        SAEROSOLMR04 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.04')
        SAEROSOLMR05 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.05')
        SAEROSOLMR06 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.06')
        SAEROSOLMR07 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.07')
        SAEROSOLMR08 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.08')
        SAEROSOLMR09 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.09')
        SAEROSOLMR10 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.10')
        SAEROSOLMR11 = FA_CAMS.readfield('S'+iLev+'AEROSOLMR.11')
        FA_CAMS.close()
        ### ==
        ### FICHIER CPL
        FA_CPL = epygram.formats.resource(CPL, 'a')
        ### --
        ### SEA SALT
        NCCNF1 = FA_CPL.readfield('S'+iLev+'N_CCN_F1')
        NCCNF1.setdata((SAEROSOLMR01.data+SAEROSOLMR02.data+SAEROSOLMR03.data)/limap[0]['mass_lima'])
        FA_CPL.writefield(NCCNF1)
        ### --
        ### SNA
        NCCNF2 = FA_CPL.readfield('S'+iLev+'N_CCN_F2')
        NCCNF2.setdata((SAEROSOLMR11.data)/limap[1]['mass_lima'])
        FA_CPL.writefield(NCCNF2)
        ### --
        ### BLACK CARBON
        NCCNF3 = FA_CPL.readfield('S'+iLev+'N_CCN_F3')
        NCCNF3.setdata((SAEROSOLMR07.data + SAEROSOLMR09.data)/limap[2]['mass_lima'])
        FA_CPL.writefield(NCCNF3)
        ### --
        NIFNF1 = FA_CPL.readfield('S'+iLev+'N_IFN_F1')
        NIFNF1.setdata((SAEROSOLMR04.data + SAEROSOLMR05.data + SAEROSOLMR06.data)/limap[3]['mass_lima'])
        FA_CPL.writefield(NIFNF1)
        ### --
        NIFNF2 = FA_CPL.readfield('S'+iLev+'N_IFN_F2')
        NIFNF2.setdata((SAEROSOLMR08.data + SAEROSOLMR10.data)/limap[4]['mass_lima'])
        FA_CPL.writefield(NIFNF2)
        ### --
        FA_CPL.close()
