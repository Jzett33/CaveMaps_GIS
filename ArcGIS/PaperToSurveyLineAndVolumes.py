# -*- coding: utf-8 -*-
"""
Convert text file from Excel to Volumes and a Survey Line using ArcGIS Pro
Generated using ArcGIS Pro 2.8.1

Jon R Zetterberg
jzett33@gmail.com
NSS67484

Last modified: 20210624

Input 0 is a text file that has been generated from the accompanying excel sheet.
Input 1 is the coordinate reference system which the coordinates in the text file reference.
Input 2 is a workspace folder. A geodatabase will be created here to store features.
Input 3 is a Yes/No option. This is to generate empty, domained point, line, and polygon
    feature classes which will hold the cave map information as it is digitized. This
    should be Yes if this is a new cave survey and no if a geodatabase already exists.

The output will be a geodatabase containing a Survey feature dataset. This will contain
    a multipatch CaveModel, ProfileCFLines which show the vertical profile of the cave
    with the ceiling and floor lines, SurveyLine which is the surveyed center line,
    and SurveyPoints which are the survey stations with attribution.
    The optional feature dataset is CaveFeatures and will contain Points, Lines, and
    Polygons. These feature classes are set with domains and attribution options to
    store digitized cave features to be shown on a final map.
"""
import arcpy
import os
"""
textfile = arcpy.GetParameterAsText(0)  #the text file generated from Excel
crs = arcpy.GetParameterAsText(1)       #coordinate reference system that the text file uses
wrkspce = arcpy.GetParameterAsText(2)   #workspace folder to generate features in
newAppend = arcpy.GetParameterAsText(3) #Do mapping layers need to be created (Yes or No)
"""
textfile = "C:\\Users\\JONZET\\Documents\\Data\\Maps\\GoatCave\\Notes\\SurveyData\\20211008\\GoatCave_20211008.txt"
#crs = arcpy.SpatialReference(26916) #UTM16N
crs = arcpy.SpatialReference(102604) #GA Statewide
#crs = arcpy.SpatialReference(103152) #TNSP11
wrkspce = "C:\\Users\\JONZET\\Documents\\Data\\Maps\\GoatCave\\Notes\\SurveyData\\20211008"
newAppend = "No"

arcpy.env.workspace = wrkspce
arcpy.env.overwriteOutput = True

#Create Geodatabase
out_folder_path = wrkspce
out_name = "SurveyData.gdb"
GDB = arcpy.CreateFileGDB_management(out_folder_path, out_name)

FGDB = os.path.join(wrkspce, "SurveyData.gdb")
arcpy.env.workspace = FGDB

#Create Feature Datasets to organize data
print("Creating Feature Datasets to organize data")
arcpy.CreateFeatureDataset_management(GDB, "Survey", crs)
SurveyFD = os.path.join(FGDB, "Survey")
arcpy.CreateFeatureDataset_management(GDB, "Profile", crs)
ProfileFD = os.path.join(FGDB, "Profile")
arcpy.CreateFeatureDataset_management(GDB, "DataDump", crs)
DataDumpFD = os.path.join(FGDB, "DataDump")
arcpy.CreateFeatureDataset_management(GDB, "SplitPoints", crs)
SplitPointsFD = os.path.join(FGDB, "SplitPoints")
arcpy.CreateFeatureDataset_management(GDB, "Volumes", crs)
VolumesFD = os.path.join(FGDB, "Volumes")

#Generate Survey Stations and Survey Line
print("Generating Survey Stations and Survey Line")
#arcpy.env.workspace = "wrkspce/SurveyData.gdb/Survey"
arcpy.env.workspace = SurveyFD
SurveyPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "x", "y", "Points_Survey", crs)
SurveyPnts = arcpy.FeatureClassToFeatureClass_conversion(SurveyPnts_Event, SurveyFD, "SurveyPoints")
SurLn = arcpy.PointsToLine_management(SurveyPnts, "SurveyLine", "Line", "Sort")

#Generate Profile Survey, Ceiling, and Floor Lines
print("Generating Profile Survey, Ceiling, and Floor Lines")
arcpy.env.workspace = ProfileFD
#Generate the profile survey stations and line
ProSurveyPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "Pro_X", "Pro_Y", "Points_SurveyProfile", crs)
ProSurveyPnts = arcpy.FeatureClassToFeatureClass_conversion(ProSurveyPnts_Event, ProfileFD, "ProfileSurveyPoints")
ProLn = arcpy.PointsToLine_management(ProSurveyPnts, "ProfileSurveyLine", "Line", "Sort")
#Generate the profile ceiling stations and line
ProCeilingPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "Pro_C_X", "Pro_C_Y", "Points_CeilingProfile", crs)
ProCeilingPnts = arcpy.FeatureClassToFeatureClass_conversion(ProCeilingPnts_Event, ProfileFD, "ProfileCeilingPoints")
arcpy.PointsToLine_management(ProCeilingPnts, "ProfileCeilingLine", "Line", "Sort")
#Generate the profile floor stations and line
ProFloorPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "Pro_F_X", "Pro_F_Y", "Points_FloorProfile", crs)
ProFloorPnts = arcpy.FeatureClassToFeatureClass_conversion(ProFloorPnts_Event, ProfileFD, "ProfileFloorPoints")
arcpy.PointsToLine_management(ProFloorPnts, "ProfileFloorLine", "Line", "Sort")

#Append Profile data to the Survey Data
print("Appending Profile data to the Survey Data")
ProfileCFLn = os.path.join(SurveyFD, "ProfileCFLines")
arcpy.Merge_management(["ProfileCeilingLine", "ProfileFloorLine"], ProfileCFLn, "", "ADD_SOURCE_INFO")
arcpy.Append_management(ProSurveyPnts, SurveyPnts)
arcpy.Append_management(ProLn, SurLn)

#Generate LRUD Point Cloud
print("Generating LRUD Point Cloud")
arcpy.env.workspace = DataDumpFD
    #Left Wall Points
LeftPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "X_Left", "Y_Left", "Points_Left", crs, "Z_Left")
LeftPnts = arcpy.FeatureClassToFeatureClass_conversion(LeftPnts_Event, DataDumpFD, "LeftPoints")
    #Right Wall Points
RightPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "X_Right", "Y_Right", "Points_Right", crs, "Z_Right")
RightPnts = arcpy.FeatureClassToFeatureClass_conversion(RightPnts_Event, DataDumpFD, "RightPoints")
    #Ceiling Points
CeilingPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "X", "Y", "Points_Ceiling", crs, "Z_Ceiling")
CeilingPnts = arcpy.FeatureClassToFeatureClass_conversion(CeilingPnts_Event, DataDumpFD, "CeilingPoints")
    #Floor Points
FloorPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "X", "Y", "Points_Floor", crs, "Z_Floor")
FloorPnts = arcpy.FeatureClassToFeatureClass_conversion(FloorPnts_Event, DataDumpFD, "FloorPoints")

#Merge, Group, and Split LRUD Point Cloud
print("Processing the LRUD Point Cloud")
PassagePoints = arcpy.Merge_management([LeftPnts, RightPnts, CeilingPnts, FloorPnts], "PassagePoints", "", "ADD_SOURCE_INFO")
arcpy.AddField_management(PassagePoints, "Group1", "LONG")
arcpy.AddField_management(PassagePoints, "Group2", "LONG")
arcpy.CalculateFields_management(PassagePoints, "PYTHON3", [["Group1", "!Sort! - ( !Sort! % 2)"], ["Group2", "!Sort! + ( !Sort! % 2)"]])
arcpy.env.workspace = FGDB
arcpy.SplitByAttributes_analysis(PassagePoints, SplitPointsFD, ["Line"])

#Generate Two Sets of Volumes
print("Generating two sets of Volumes")
FCList = arcpy.ListFeatureClasses("", "", "SplitPoints")
for fc in FCList:
    output1 = os.path.join(VolumesFD, fc + "_Group1")
    output2 = os.path.join(VolumesFD, fc + "_Group2")
    arcpy.MinimumBoundingVolume_3d(fc, "Shape.Z", output1, "CONVEX_HULL","LIST", "Group1")
    arcpy.MinimumBoundingVolume_3d(fc, "Shape.Z", output2, "CONVEX_HULL","LIST", "Group2")

#Merge all Volumes into a single output file
print("Merging all Volumes into a single output file")
arcpy.env.workspace = FGDB
VolList = arcpy.ListFeatureClasses("", "", "Volumes")
FinalVolumes = os.path.join(SurveyFD, "CaveModel")
arcpy.env.workspace = VolumesFD
arcpy.Merge_management(VolList, FinalVolumes, "", "ADD_SOURCE_INFO")

#Delete Temporary Workspaces
arcpy.Delete_management(SplitPointsFD)
arcpy.Delete_management(VolumesFD)
arcpy.Delete_management(DataDumpFD)
arcpy.Delete_management(ProfileFD)
print("Data Processing Completed")

#Create additional features in the geodatabase to be used as templates in map production
if newAppend == "Yes":
    print("Mapping feature classes creation started")
    #Generate domains that will be used in map production
    arcpy.CreateDomain_management(FGDB, "PointTypes", "", "TEXT")
    arcpy.CreateDomain_management(FGDB, "LineTypes", "", "TEXT")
    arcpy.CreateDomain_management(FGDB, "PolygonTypes", "", "TEXT")
    arcpy.CreateDomain_management(FGDB, "TrueFalse", "", "TEXT")
    domDict1 = {"30":"Flowstone", "31":"Stalagmite", "32":"Stalactite", "33":"Column",
                "34":"Soda Straw", "20":"Drop", "21":"Ceiling", "41":"Rock",
                "40":"Slope", "10":"Datum", "11":"Tree", "12":"XS Label",
                "50":"Tire", "51":"Trash", "52":"Organic Debris", "53":"Bolt"}
    for code in domDict1:        
        arcpy.AddCodedValueToDomain_management(FGDB, "PointTypes", code, domDict1[code])
    domDict2 = {"12":"Ceiling Drop", "13":"Floor Drop", "10":"Wall", "30":"Flowing Water",
                "11":"Approximate Wall", "14":"Lower Level", "15":"Upper Level", "20":"XS Location"}
    for code in domDict2:        
        arcpy.AddCodedValueToDomain_management(FGDB, "LineTypes", code, domDict2[code])
    domDict3 = {"10":"Cave Outline", "21":"Pillar", "30":"Rock", "40":"Water Pool",
                "20":"Formation"}
    for code in domDict3:        
        arcpy.AddCodedValueToDomain_management(FGDB, "PolygonTypes", code, domDict3[code])
    domDict4 = {"1":"True", "0":"False"}
    for code in domDict4:
        arcpy.AddCodedValueToDomain_management(FGDB, "TrueFalse", code, domDict4[code])
    #Generate cave feature templates to be used in map production
    arcpy.CreateFeatureDataset_management(FGDB, "CaveFeatures", crs)
    caveFeat = os.path.join(FGDB, "CaveFeatures")
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
    caveFeatPolygons = arcpy.CreateFeatureclass_management(caveFeat, "Polygons", "POLYGON")
    arcpy.AddField_management(caveFeatPolygons, "PolygonType", "TEXT", "", "", "50", "Point Type", "", "", "PolygonTypes")
    arcpy.AddField_management(caveFeatPolygons, "Level", "SHORT")
    arcpy.AddField_management(caveFeatPolygons, "Shown", "TEXT", "", "", "5", "Point Type", "", "", "TrueFalse")
    print("Mapping feature classes creation completed")
