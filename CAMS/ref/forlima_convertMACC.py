#!/usr/bin/en python
# -*- coding: utf-8 -*-

import epygram
epygram.init_env()
import numpy
import os
import shutil
from epygram.geometries.VGeometry import hybridP2pressure

fichierMacc='FicIN'
fichierAROME="GuessOUT"
fichierOut="FicOUT"


r=epygram.formats.resource(filename=fichierMacc,openmode='a')

aerosols=['SEA.SALT1','SEA.SALT2','SEA.SALT3','DES.DUST1','DES.DUST','DES.DUST3','ORG.MAT1','ORG.MAT2','BLACK.CAR1','BLACK.CAR2','SULPHATE']
#1-3:Sea Salt->CCN_F1, 4-6:Dust->IFN_F1,7 et 9:Hydrophobic OM BC-> IFN_F2,8et10 : hydrophylic OM BC -> Coated IFN (CCN_F3), 11: Sulfates -> CCN_F2 
#N_CCN_F1: SEA.SALT1+SEA.SALT2+SEA.SALT3
#N_CCN_F2: SULPHATE
#N_CCN_F3: ORG.MAT1+BLACK.CAR1 (hydrophylic)
#N_IFN_F1: DES.DUST1+DES.DUST2+DES.DUST3
#N_IFN_F2: ORG.MAT2+BLACK.CAR2 (hydrophobic)

#lima_aerosols=[[aerosols[10]],[aerosols[0],aerosols[1],aerosols[2]],[aerosols[7],aerosols[9]],[aerosols[6],aerosols[8]],[aerosols[3],aerosols[4],aerosols[5]]]
#lima_aerosols=[[aerosols[0],aerosols[1],aerosols[2]],[aerosols[10]],[aerosols[7],aerosols[9]],[aerosols[6],aerosols[8]],[aerosols[3],aerosols[4],aerosols[5]]]
limaname=['N_CCN_F1','N_CCN_F2','N_CCN_F3','N_IFN_F1','N_IFN_F2']
#valeurs MACC
rho_lima=[2160,2000,1750,2300,1700]
dm_lima=[0.8,0.5,0.2,0.8,0.2] # in micrometer!
sigma_lima=[1.89,1.6,1.6,1.9,1.6]

mass_lima = [0]*5

if os.path.exists(fichierOut): os.remove(fichierOut)
shutil.copy(fichierAROME, fichierOut) #Recopie du fichier AROME en entrée
fOut=epygram.formats.resource(filename=fichierOut,openmode='a',fmt='FA') #Ouverture de la copie en mode append


#il faut ensuite ici pour chaque limaname en bouclant sur les niveaux verticaux :
#1) calculer le facteur pour passer de masse a concentration :
#  mass_lima[i] = float(rho_lima[i])*4.0/3.0*numpy.pi*((dm_lima[i]*1e-06/2.0)**3)*(numpy.exp(9.0/2.0*numpy.log(sigma_lima[i])**2))
#2)lire les champs requits dans fichierMACC, calculer la masse totale en ajoutant les variables quand c'est necessaire (ex CCN_F1 il faut ajouter la masse des 3 SEA_SALT puis
#3) convertir la masse en concentration en divisant par mass_lima[i]
#4) ecrire le resultat dans fichierOut
for i in range(len(limaname)):
  mass_lima[i] = float(rho_lima[i])*4.0/3.0*numpy.pi*((dm_lima[i]*1e-06/2.0)**3)*(numpy.exp(9.0/2.0*numpy.log(sigma_lima[i])**2))

#recuperation du nb de niveaux :
champ2DAromeLNSP = fOut.readfield("SURFPRESSION")
resultat = champ2DAromeLNSP
if champ2DAromeLNSP.spectral: champ2DAromeLNSP.sp2gp()
champ2DAromeLNSP.operation('exp')
vert_coord_as_pressure = hybridP2pressure(fOut.geometry.vcoordinate, Psurf=champ2DAromeLNSP.data, vertical_mean='geometric')

for niv in range(len(vert_coord_as_pressure.levels)):
   #0.fieldN_CCN_F1
   i=0
   field1=r.readfield('S'+ str(niv+1).zfill(3)+'SEA.SALT1')
   field2=r.readfield('S'+ str(niv+1).zfill(3)+'SEA.SALT2')
   field3=r.readfield('S'+ str(niv+1).zfill(3)+'SEA.SALT3')
   resultat.setdata((field1.data+field2.data+field3.data)/mass_lima[i])
   fieldres =  'S'+ str(niv+1).zfill(3) +limaname[i]
   resultat.fid['FA']=fieldres
   fOut.writefield(resultat)
for niv in range(len(vert_coord_as_pressure.levels)):
   #1.fieldN_CCN_F2
   i=1
   field1=r.readfield('S'+ str(niv+1).zfill(3)+'SULPHATE')
   resultat.setdata(field1.data/mass_lima[i])
   fieldres =  'S'+ str(niv+1).zfill(3) +limaname[i]
   resultat.fid['FA']=fieldres
   fOut.writefield(resultat)
for niv in range(len(vert_coord_as_pressure.levels)):
   #2.fieldN_CCN_F3
   i=2
   field1=r.readfield('S'+ str(niv+1).zfill(3)+'ORG.MAT1')
   field2=r.readfield('S'+ str(niv+1).zfill(3)+'BLACK.CAR1')
   resultat.setdata((field1.data+field2.data)/mass_lima[i])
   fieldres =  'S'+ str(niv+1).zfill(3) +limaname[i]
   resultat.fid['FA']=fieldres
   fOut.writefield(resultat)
for niv in range(len(vert_coord_as_pressure.levels)):
   #3.N_IFN_F1
   i=3
   field1=r.readfield('S'+ str(niv+1).zfill(3)+'DES.DUST1')
   field2=r.readfield('S'+ str(niv+1).zfill(3)+'DES.DUST2')
   field3=r.readfield('S'+ str(niv+1).zfill(3)+'DES.DUST3')
   resultat.setdata((field1.data+field2.data+field3.data)/mass_lima[i])
   fieldres =  'S'+ str(niv+1).zfill(3) +limaname[i]
   resultat.fid['FA']=fieldres
   fOut.writefield(resultat)
for niv in range(len(vert_coord_as_pressure.levels)):
   #4.N_IFN_F1
   i=4
   field1=r.readfield('S'+ str(niv+1).zfill(3)+'ORG.MAT2')
   field2=r.readfield('S'+ str(niv+1).zfill(3)+'BLACK.CAR2')
   resultat.setdata((field1.data+field2.data)/mass_lima[i])
   fieldres =  'S'+ str(niv+1).zfill(3) +limaname[i]
   resultat.fid['FA']=fieldres
   fOut.writefield(resultat)

  
r.close()
fOut.close()
