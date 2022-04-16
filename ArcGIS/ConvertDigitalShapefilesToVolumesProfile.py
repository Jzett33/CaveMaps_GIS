# -*- coding: utf-8 -*-
"""
Convert Therion Export Shapefiles to Volumes using ArcGIS Pro
Developed using Therion 5.5.3 and ArcGIS Pro 2.9.0

There is a known difference between versions 2.8 and 2.9 where the Spatial Outlier Detection
    tool generates a field called NTHDIST instead of LOF which is used in this script

Jon R Zetterberg
jzett33@gmail.com
NSS67484

Last modified: 20220403

Input 0 is a folder containing the output Therion shots3d and stations3d shapefiles.
Input 1 is the coordinate reference system which the shapefiles reference.
Input 2 is a Yes/No option. This is to generate empty, domained point, line, and polygon
    feature classes which will hold the cave map information as it is digitized. This
    should be Yes if this is a new cave survey and no if a geodatabase already exists.

The output will be a geodatabase containing a SmoothedVolume feature dataset. This will
    contain a multipatch called AllVolumes which shows the cave using all available splay
    shots and has been smoothed between stations. A secondary multipatch called
    AllVolumes_Simplified shows the same information, but has not be through the smoothing
    process.
    The optional feature dataset is CaveFeatures and will contain Points, Lines, and
    Polygons. These feature classes are set with domains and attribution options to
    store digitized cave features to be shown on a final map.
"""

import arcpy
import os
"""
thFolder = arcpy.GetParameterAsText(0) #The folder containing the output shapefiles from Therion
textfile = arcpy.GetParameterAsText(1)  #the zed file generated from Excel
crs = arcpy.GetParameterAsText(2)      #coordinate reference system that the Therion files use
createProfile = arcpy.GetParameterAsText(3) #Does a profile need to be processed from the specified text file (Yes or No)
newAppend = arcpy.GetParameterAsText(4)#Do mapping layers need to be created (Yes or No)
"""
thFolder = "C:\\Users\\JONZET\\Documents\\Data\\Maps\\SaucerfullOfSecret\\Notes\\SurveyData\\Saucer\\"
textfile = "C:\\Users\\JONZET\\Documents\\Data\\Maps\\SaucerfullOfSecret\\Notes\\SurveyData\\Saucer_Profile.txt"
crs = arcpy.SpatialReference(26916)
createProfile = "Yes"
newAppend = "Yes"

arcpy.env.workspace = thFolder
arcpy.env.overwriteOutput = True

shots = os.path.join(thFolder, "shots3d.shp")
stations = os.path.join(thFolder, "stations3d.shp")

#Create file geodatabase to store features
arcpy.CreateFileGDB_management(thFolder, "Workspace.gdb")
fileGDB = os.path.join(thFolder, "Workspace.gdb")
arcpy.env.workspace = fileGDB

#Import survey data to Geodatabase
arcpy.CreateFeatureDataset_management(fileGDB, "SurveyData", crs)
surveyData = os.path.join(fileGDB, "SurveyData")
shotsFC = arcpy.FeatureClassToFeatureClass_conversion(shots, surveyData, "Shots")
stationsFC = arcpy.FeatureClassToFeatureClass_conversion(stations, surveyData, "Stations")
arcpy.Delete_management(shots)
arcpy.Delete_management(stations)
shots = shotsFC
stations = stationsFC

#Format survey data
arcpy.AddField_management(stations, "FromSta", "TEXT")
arcpy.CalculateField_management(stations, "FromSta", '!_NAME!.replace(".", "_")', "PYTHON3")
arcpy.AddGeometryAttributes_management(stations, "POINT_X_Y_Z_M")
arcpy.DeleteField_management(stations, ["POINT_M"])
arcpy.AddGeometryAttributes_management(shots, "LENGTH_3D", "METERS")

#Create Feature Datasets to better organize data
print("Creating Feature Datasets to organize data")
arcpy.CreateFeatureDataset_management(fileGDB, "TempPoints", crs)
tPnts = os.path.join(fileGDB, "TempPoints")
arcpy.CreateFeatureDataset_management(fileGDB, "SmoothedVolume", crs)
sVols = os.path.join(fileGDB, "SmoothedVolume")
arcpy.CreateFeatureDataset_management(fileGDB, "TempVolumes", crs)
tVols = os.path.join(fileGDB, "TempVolumes")
mergedPoints = arcpy.CreateFeatureclass_management(tPnts, "MergedPoints", "POINT", stations, "", "ENABLED")
arcpy.CreateFeatureDataset_management(fileGDB, "TempSplays", crs)
tSplays = os.path.join(fileGDB, "TempSplays")
arcpy.CreateFeatureDataset_management(fileGDB, "LongShotCheck", crs)
longSC = os.path.join(fileGDB, "LongShotCheck")
arcpy.CreateFeatureDataset_management(fileGDB, "Profile", crs)
ProfileFD = os.path.join(fileGDB, "Profile")

#Check for long shots, delete if any are found
staLSC = arcpy.FeatureClassToFeatureClass_conversion(stations, longSC, "Stations_LSC")
staLSCPath = fr"{longSC}\Stations_LSC_Values"
outliers = arcpy.stats.SpatialOutlierDetection(staLSC, staLSCPath, "10")
excldedShots = arcpy.FeatureClassToFeatureClass_conversion(outliers, surveyData, "ExcludedShots", '"NTHDIST" > 3')
stationsLYR_LSC = arcpy.MakeFeatureLayer_management(stations, "stationsLYR_LSC")
arcpy.SelectLayerByLocation_management("stationsLYR_LSC", "INTERSECT_3D", excldedShots)
arcpy.DeleteFeatures_management(stationsLYR_LSC)
shotsLYR_LSC = arcpy.MakeFeatureLayer_management(shots, "shotsLYR_LSC")
arcpy.SelectLayerByLocation_management("shotsLYR_LSC", "INTERSECT_3D", excldedShots)
arcpy.DeleteFeatures_management(shotsLYR_LSC)
arcpy.Delete_management(staLSC)
arcpy.Delete_management(outliers)

#Seperate splay shots out from the center line
splays = arcpy.FeatureClassToFeatureClass_conversion(shots, fileGDB, "SplayShots", '"_SPLAY" = 1')
arcpy.SplitByAttributes_analysis(splays, tSplays, "_From")
splayList = arcpy.ListFeatureClasses("", "", "TempSplays")

arcpy.MakeFeatureLayer_management(stations, "stationsLYR")

for selectedSplays in splayList:
    arcpy.SelectLayerByLocation_management("stationsLYR", "INTERSECT_3D", selectedSplays)
    desc = arcpy.Describe(selectedSplays)
    FromStaVal = str(desc.baseName)
    #Issue lies here in passing the FromStaVal into the field calculation when running in a toolbox
    arcpy.CalculateField_management("stationsLYR", "FromSta", 'FromStaVal')
    arcpy.Append_management("stationsLYR", mergedPoints, "NO_TEST")

arcpy.AddField_management(mergedPoints, "StaInt", "SHORT")
arcpy.CalculateField_management(mergedPoints, "StaInt", '!FromSta!.replace("T", "")')
dissolvePath = fr"{tPnts}\DissolvedPoints"
dissolvedPnts = arcpy.Dissolve_management(mergedPoints, dissolvePath, ["StaInt"])

arcpy.CalculateField_management(dissolvedPnts, "StationNumber", '!OBJECTID!', "PYTHON3", "", "SHORT")
arcpy.CalculateField_management(dissolvedPnts, "Group1", '!StaInt! - ( !StaInt! % 2)', "PYTHON3", "", "SHORT")
arcpy.CalculateField_management(dissolvedPnts, "Group2", '!StaInt! + ( !StaInt! % 2)', "PYTHON3", "", "SHORT")

vol1Path = fr"{tVols}\Group1Vols"
vol2Path = fr"{tVols}\Group2Vols"
arcpy.MinimumBoundingVolume_3d(dissolvedPnts, 'Shape.Z', vol1Path, "CONVEX_HULL", "LIST", "Group1")
arcpy.MinimumBoundingVolume_3d(dissolvedPnts, 'Shape.Z', vol2Path, "CONVEX_HULL", "LIST", "Group2")

mergePath = fr"{sVols}\AllVolumes"
mergePath2 = fr"{sVols}\AllVolumes_Simplified"
arcpy.Merge_management([vol1Path, vol2Path], mergePath)
arcpy.MinimumBoundingVolume_3d(dissolvedPnts, 'Shape.Z', mergePath2, "CONVEX_HULL", "LIST", "StaInt")

#delete temp processing files
arcpy.Delete_management(tPnts)
arcpy.Delete_management(tVols)
arcpy.Delete_management(tSplays)
arcpy.Delete_management(splays)
arcpy.Delete_management(longSC)

#Create profile survey, ceiling, and floor lines
if createProfile == "YES":
    createProfile = "Yes"
if createProfile == "yes":
    createProfile = "Yes"
if createProfile == "y":
    createProfile = "Yes"
if createProfile == "Y":
    createProfile = "Yes"
if createProfile == "Yes":
    print("Generating Profile Survey, Ceiling, and Floor Lines")
    arcpy.env.workspace = ProfileFD
    #Generate the profile survey stations and line
    ProSurveyPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "Pro_X", "Pro_Y", "Points_SurveyProfile", crs)
    ProSurveyPnts = arcpy.FeatureClassToFeatureClass_conversion(ProSurveyPnts_Event, ProfileFD, "ProfileSurveyPoints")
    ProLn = arcpy.PointsToLine_management(ProSurveyPnts, "ProfileSurveyLine", "Line", "Sort")

#Create additional features in the geodatabase to be used as templates in map production
if newAppend == "YES":
    newAppend = "Yes"
if newAppend == "yes":
    newAppend = "Yes"
if newAppend == "y":
    newAppend = "Yes"
if newAppend == "Y":
    newAppend = "Yes"
if newAppend == "Yes":
    print("Mapping feature classes creation started")
    #Generate domains that will be used in map production
    arcpy.CreateDomain_management(fileGDB, "PointTypes", "", "TEXT")
    arcpy.CreateDomain_management(fileGDB, "LineTypes", "", "TEXT")
    arcpy.CreateDomain_management(fileGDB, "PolygonTypes", "", "TEXT")
    arcpy.CreateDomain_management(fileGDB, "TrueFalse", "", "TEXT")
    domDict1 = {"30":"Flowstone", "31":"Stalagmite", "32":"Stalactite", "33":"Column",
                "34":"Soda Straw", "20":"Drop", "21":"Ceiling", "41":"Rock",
                "40":"Slope", "10":"Datum", "11":"Tree", "12":"XS Label",
                "50":"Tire", "51":"Trash", "52":"Organic Debris", "53":"Bolt",
                "13":"Above Datum", "14":"Below Datum", "22":"Air over Water"}
    for code in domDict1:        
        arcpy.AddCodedValueToDomain_management(fileGDB, "PointTypes", code, domDict1[code])
    domDict2 = {"12":"Ceiling Drop", "13":"Floor Drop", "10":"Wall", "30":"Flowing Water",
                "11":"Approximate Wall", "14":"Lower Level", "15":"Upper Level", "20":"XS Location"}
    for code in domDict2:        
        arcpy.AddCodedValueToDomain_management(fileGDB, "LineTypes", code, domDict2[code])
    domDict3 = {"10":"Cave Outline", "21":"Pillar", "30":"Rock", "40":"Water Pool",
                "20":"Formation"}
    for code in domDict3:        
        arcpy.AddCodedValueToDomain_management(fileGDB, "PolygonTypes", code, domDict3[code])
    domDict4 = {"1":"True", "0":"False"}
    for code in domDict4:
        arcpy.AddCodedValueToDomain_management(fileGDB, "TrueFalse", code, domDict4[code])
    #Generate cave feature templates to be used in map production
    arcpy.CreateFeatureDataset_management(fileGDB, "CaveFeatures", crs)
    caveFeat = os.path.join(fileGDB, "CaveFeatures")
    #Generate point, line, and polygon feature classes which will hold map features
    caveFeatPoints = arcpy.CreateFeatureclass_management(caveFeat, "Points", "POINT")
    arcpy.AddField_management(caveFeatPoints, "PointType", "TEXT", "", "", "50", "Point Type", "", "", "PointTypes")
    arcpy.AddField_management(caveFeatPoints, "Level", "SHORT")
    arcpy.AddField_management(caveFeatPoints, "Rotation", "SHORT")
    arcpy.AddField_management(caveFeatPoints, "Label", "TEXT", "", "", "50")
    arcpy.AddField_management(caveFeatPoints, "Shown", "TEXT", "", "", "5", "Point Type", "", "", "TrueFalse")
    caveFeatLines = arcpy.CreateFeatureclass_management(caveFeat, "Lines", "POLYLINE")
    arcpy.AddField_management(caveFeatLines, "LineType", "TEXT", "", "", "50", "Point Type", "", "", "LineTypes")
    arcpy.AddField_management(caveFeatLines, "Level", "SHORT")
    arcpy.AddField_management(caveFeatLines, "Label", "TEXT", "", "", "50")
    arcpy.AddField_management(caveFeatLines, "Shown", "TEXT", "", "", "5", "Point Type", "", "", "TrueFalse")
    caveFeatLines = arcpy.CreateFeatureclass_management(caveFeat, "CenterLine", "POLYLINE")
    arcpy.AddField_management(caveFeatLines, "Level", "SHORT")
    caveFeatPolygons = arcpy.CreateFeatureclass_management(caveFeat, "Polygons", "POLYGON")
    arcpy.AddField_management(caveFeatPolygons, "PolygonType", "TEXT", "", "", "50", "Point Type", "", "", "PolygonTypes")
    arcpy.AddField_management(caveFeatPolygons, "Level", "SHORT")
    arcpy.AddField_management(caveFeatPolygons, "Shown", "TEXT", "", "", "5", "Point Type", "", "", "TrueFalse")
    print("Mapping feature classes creation completed")
