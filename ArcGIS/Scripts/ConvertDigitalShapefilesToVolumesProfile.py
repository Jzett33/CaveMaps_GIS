# -*- coding: utf-8 -*-
"""
Convert Therion Export Shapefiles to Volumes using ArcGIS Pro
Developed using Therion 5.5.3 and ArcGIS Pro 3.6.2

Jon R Zetterberg
jzett33@gmail.com
NSS67484

Last modified: 20260406

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
createLeads = arcpy.GetParameterAsText(5) #Should a leads layer be generated (Yes or No)
go3D = arcpy.GetParameterAsText(6) #Should a 3D model be generated (Yes or No)
"""

arcpy.env.workspace = thFolder
arcpy.env.overwriteOutput = True

shots = os.path.join(thFolder, "shots3d.shp")
stations = os.path.join(thFolder, "stations3d.shp")

#Create file geodatabase to store features
print("Reformatting Survey Data")
arcpy.CreateFileGDB_management(thFolder, "Workspace.gdb")
fileGDB = os.path.join(thFolder, "Workspace.gdb")
arcpy.env.workspace = fileGDB

#Import survey data to Geodatabase
arcpy.CreateFeatureDataset_management(fileGDB, "SurveyData", crs)
surveyData = os.path.join(fileGDB, "SurveyData")
shotsFC = arcpy.FeatureClassToFeatureClass_conversion(shots, surveyData, "Shots")
stationsFC = arcpy.FeatureClassToFeatureClass_conversion(stations, surveyData, "AllStations")
arcpy.Delete_management(shots)
arcpy.Delete_management(stations)
shots = shotsFC
stations = stationsFC

#Format survey data
arcpy.AddField_management(stations, "FromSta", "TEXT")
arcpy.CalculateField_management(stations, "FromSta", '!_NAME!.replace(".", "_")', "PYTHON3")
arcpy.management.CalculateGeometryAttributes(stations, [["X", "POINT_X"], ["Y", "POINT_Y"], ["Z", "POINT_Z"]])  #Pro 3.0+
arcpy.AddGeometryAttributes_management(shots, "LENGTH_3D", "METERS")   #Pro 3.0+

#Create Feature Datasets to better organize data
print("Creating Feature Datasets to organize data")
arcpy.CreateFeatureDataset_management(fileGDB, "TempPoints", crs)
tPnts = os.path.join(fileGDB, "TempPoints")
arcpy.CreateFeatureDataset_management(fileGDB, "CaveModels", crs)
sVols = os.path.join(fileGDB, "CaveModels")
mergedPoints = arcpy.CreateFeatureclass_management(tPnts, "MergedPoints", "POINT", stations, "", "ENABLED")
arcpy.CreateFeatureDataset_management(fileGDB, "TempSplays", crs)
tSplays = os.path.join(fileGDB, "TempSplays")
arcpy.CreateFeatureDataset_management(fileGDB, "LongShotCheck", crs)
longSC = os.path.join(fileGDB, "LongShotCheck")
arcpy.CreateFeatureDataset_management(fileGDB, "TempLegs", crs)
tLegs = os.path.join(fileGDB, "TempLegs")

#Check for long shots, delete if any are found
print("Checking for longshots")
staLSC = arcpy.FeatureClassToFeatureClass_conversion(stations, longSC, "Stations_LSC")
staLSCPath = fr"{longSC}\Stations_LSC_Values"
outliers = arcpy.stats.SpatialOutlierDetection(staLSC, staLSCPath)
excldedShots = arcpy.FeatureClassToFeatureClass_conversion(outliers, surveyData, "ExcludedShots", '"NTHDIST" > 11')
stationsLYR_LSC = arcpy.MakeFeatureLayer_management(stations, "stationsLYR_LSC")
arcpy.SelectLayerByLocation_management("stationsLYR_LSC", "INTERSECT_3D", excldedShots)
arcpy.DeleteFeatures_management(stationsLYR_LSC)
shotsLYR_LSC = arcpy.MakeFeatureLayer_management(shots, "shotsLYR_LSC")
arcpy.SelectLayerByLocation_management("shotsLYR_LSC", "INTERSECT_3D", excldedShots)
arcpy.DeleteFeatures_management(shotsLYR_LSC)
arcpy.Delete_management(staLSC)
arcpy.Delete_management(outliers)
#Delete feature class if none are found
longCount = arcpy.GetCount_management(excldedShots)
if str(longCount) == "0":
	arcpy.Delete_management(excldedShots)

#Seperate splays out from the legs
print("Attributing splay shots")
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

#Caclulate survey statistics and display
#Caclulate horizontal and 3D lengths
legOnly = arcpy.FeatureClassToFeatureClass_conversion(shots, "", "LegsOnly", '"_SPLAY" = 0')
hLenTable = arcpy.analysis.Statistics(legOnly, "ShotsStats_HorizontalLen", [["Shape_Length", "SUM"], ["Shape_Length", "MEAN"],
                                                                            ["Shape_Length", "MIN"], ["Shape_Length", "MAX"],
                                                                            ["Shape_Length", "RANGE"], ["Shape_Length", "STD"],
                                                                            ["Shape_Length", "MEDIAN"]])
tLenTable = arcpy.analysis.Statistics(legOnly, "ShotsStats_TrueLen", [["LENGTH_3D", "SUM"], ["LENGTH_3D", "MEAN"],
                                                                      ["LENGTH_3D", "MIN"], ["LENGTH_3D", "MAX"],
                                                                      ["LENGTH_3D", "RANGE"], ["LENGTH_3D", "STD"],
                                                                      ["LENGTH_3D", "MEDIAN"]])
cursor2 = arcpy.SearchCursor(tLenTable)
for row2 in cursor2:
        tft = round((row2.SUM_LENGTH_3D)*3.28084)
        print("Surveyed Length: {1} feet, {0} meters".format(round(row2.SUM_LENGTH_3D), tft))
del cursor2, row2
cursor1 = arcpy.SearchCursor(hLenTable)
for row1 in cursor1:
        hft = round((row1.SUM_Shape_Length)*3.28084)
        print("Horizontal Length: {1} feet, {0} meters".format(round(row1.SUM_Shape_Length), hft))
del cursor1, row1

#Caclulate vertical extent
arcpy.management.CalculateGeometryAttributes(mergedPoints, [["X", "POINT_X"], ["Y", "POINT_Y"], ["Z", "POINT_Z"]])
staTable = arcpy.Statistics_analysis(mergedPoints, "StationStats", [["Z", "MEAN"], ["Z", "MIN"], ["Z", "MAX"],["Z", "RANGE"],
                                                                    ["Z", "STD"], ["Z", "COUNT"], ["Z", "MEDIAN"]])
cursor3 = arcpy.SearchCursor(staTable)
for row3 in cursor3:
        veft = round((row3.RANGE_Z)*3.28084)
        print("Vertical Extent: {1} feet, {0} meters".format(round(row3.RANGE_Z), veft))
del cursor3, row3
#Create and populate cave summary table
print("Calculating additional statistics for the survey.")
stats = arcpy.management.CreateTable(fileGDB, "CaveStatistics1")
#a=true b=horizontal c=station d=derived
arcpy.management.AddFields(stats, [["SurveyLengthM", "DOUBLE", "Survey Length Meters"],         #1      a
                                   ["SurveyLengthF", "DOUBLE", "Survey Length Feet"],           #2      d
                                   ["HorizontalLengthM", "DOUBLE", "Horizontal Length Meters"], #3      b
                                   ["HorizontalLengthF", "DOUBLE", "Horizontal Length Feet"],   #4      d
                                   ["VerticalExtentM", "DOUBLE", "Vertical Extent Meters"],     #5      c
                                   ["VerticalExtentF", "DOUBLE", "Vertical Extent Feet"],       #6      d
                                   ["AverageShotM", "DOUBLE", "Average Shot Length Meters"],    #7      a
                                   ["AverageShotF", "DOUBLE", "Average Shot Length Feet"],      #8      d
                                   ["NumShots", "LONG", "Number of Shots"],                     #9      a
                                   ["NumStations", "LONG", "Number of Stations"],               #10     d
                                   ["NumSplay", "LONG", "Number of Splays"],                    #11     c+d
                                   ["LongShotM", "DOUBLE", "Longest Shot Meters"],              #12     a
                                   ["LongShotF", "DOUBLE", "Longest Shot Feet"],                #13     d
                                   ["ShortShotM", "DOUBLE", "Shortest Shot Meters"],            #14     a
                                   ["ShortShotF", "DOUBLE", "Shortest Shot Feet"],              #15     d
                                   ["LowPointM", "DOUBLE", "Lowest Point Meters"],              #16     c
                                   ["LowPointF", "DOUBLE", "Lowest Point Feet"],                #17     d
                                   ["HighPointM", "DOUBLE", "Highest Point Meters"],            #18     c
                                   ["HighPointF", "DOUBLE", "Highest Point Feet"]])             #19     d
#Unable to figure out the field mapping with multiple inputs. Following section of code was copied from the tool input
arcpy.management.Append(
    inputs=tLenTable,
    target=stats,
    schema_type="NO_TEST",
    field_mapping='SurveyLengthM "Survey Length Meters" true true false 8 Double 0 0,First,#,ShotsStats_TrueLen,SUM_LENGTH_3D,-1,-1;AverageShotM "Average Shot Length Meters" true true false 8 Double 0 0,First,#,ShotsStats_TrueLen,MEAN_LENGTH_3D,-1,-1;NumShots "Number of Shots" true true false 4 Long 0 0,First,#,ShotsStats_TrueLen,FREQUENCY,-1,-1;LongShotM "Longest Shot Meters" true true false 8 Double 0 0,First,#,ShotsStats_TrueLen,MAX_LENGTH_3D,-1,-1;ShortShotM "Shortest Shot Meters" true true false 8 Double 0 0,First,#,ShotsStats_TrueLen,MIN_LENGTH_3D,-1,-1',
    subtype="",
    expression="",
    match_fields=None,
    update_geometry="NOT_UPDATE_GEOMETRY",
    enforce_domains="NO_ENFORCE_DOMAINS")
#and all these joins and calculations are to do the rest
hJoin = arcpy.management.AddJoin(stats, "OBJECTID", hLenTable, "OBJECTID")
sJoin = arcpy.management.AddJoin(hJoin, "OBJECTID", staTable, "OBJECTID")
cStats = arcpy.conversion.ExportTable(sJoin, "CaveStatistics")
arcpy.Delete_management([sJoin, hJoin, staTable, hLenTable, tLenTable, stats])
arcpy.management.CalculateField(cStats, "HorizontalLengthM", "!SUM_Shape_Length!", "PYTHON3")
arcpy.management.CalculateField(cStats, "VerticalExtentM", "!RANGE_Z!", "PYTHON3")
arcpy.management.CalculateField(cStats, "NumSplay", "!FREQUENCY_1!", "PYTHON3")
arcpy.management.CalculateField(cStats, "LowPointM", "!MIN_Z!", "PYTHON3")
arcpy.management.CalculateField(cStats, "HighPointM", "!MAX_Z!", "PYTHON3")
arcpy.management.DeleteField(cStats, ["OBJECTID_1", "FREQUENCY", "SUM_Shape_Length", "MEAN_Shape_Length",
                                      "MIN_Shape_Length", "MAX_Shape_Length", "RANGE_Shape_Length",
                                      "STD_Shape_Length", "MEDIAN_Shape_Length", "OBJECTID_12", "FREQUENCY_1",
                                      "MEAN_Z", "MIN_Z", "MAX_Z", "RANGE_Z", "STD_Z", "COUNT_Z", "MEDIAN_Z"])
arcpy.management.CalculateField(cStats, "SurveyLengthF", "!SurveyLengthM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "HorizontalLengthF", "!HorizontalLengthM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "VerticalExtentF", "!VerticalExtentM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "AverageShotF", "!AverageShotM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "NumStations", "!NumShots!+1", "PYTHON3")
arcpy.management.CalculateField(cStats, "NumSplay", "!NumSplay!-!NumShots!", "PYTHON3")
arcpy.management.CalculateField(cStats, "LongShotF", "!LongShotM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "ShortShotF", "!ShortShotM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "LowPointF", "!LowPointM!*3.28084", "PYTHON3")
arcpy.management.CalculateField(cStats, "HighPointF", "!HighPointM!*3.28084", "PYTHON3")

#Caclulate passage height at each station
staSumm = arcpy.analysis.Statistics(stations, "StationZSummary", "Z COUNT;Z MEAN;Z MIN;Z MAX;Z RANGE", "FromSta")
outfc = os.path.join(surveyData, "Stations2")
justStations = arcpy.conversion.ExportFeatures(
    in_features="AllStations",
    out_features=outfc,
    where_clause="_NAME <> '.'",
    use_field_alias_as_name="NOT_USE_ALIAS",
    field_mapping='_ID "_ID" true true false 2 Short 0 0,First,#,AllStations,_ID,-1,-1;_UID "_UID" true true false 2 Short 0 0,First,#,AllStations,_UID,-1,-1;_NAME "_NAME" true true false 4 Text 0 0,First,#,AllStations,_NAME,0,3;_SURVEY "_SURVEY" true true false 9 Text 0 0,First,#,AllStations,_SURVEY,0,8;_SURFACE "_SURFACE" true true false 2 Short 0 0,First,#,AllStations,_SURFACE,-1,-1;_FIXED "_FIXED" true true false 2 Short 0 0,First,#,AllStations,_FIXED,-1,-1;_ENTRANCE "_ENTRANCE" true true false 2 Short 0 0,First,#,AllStations,_ENTRANCE,-1,-1;_CONTINUA_ "_CONTINUA_" true true false 2 Short 0 0,First,#,AllStations,_CONTINUA_,-1,-1;FromSta "FromSta" true true false 255 Text 0 0,First,#,AllStations,FromSta,0,254;X "X" true true false 8 Double 0 0,First,#,AllStations,X,-1,-1;Y "Y" true true false 8 Double 0 0,First,#,AllStations,Y,-1,-1;Z "Z" true true false 8 Double 0 0,First,#,AllStations,Z,-1,-1',
    sort_field=None)
arcpy.AddField_management(justStations, "CeilingZ", "DOUBLE")
arcpy.AddField_management(justStations, "FloorZ", "DOUBLE")
arcpy.AddField_management(justStations, "PassageHeightM", "DOUBLE","",1)
arcpy.AddField_management(justStations, "PassageHeightFt", "DOUBLE","",1)
staJoin = arcpy.management.AddJoin(justStations, "FromSta", staSumm, "FromSta")
outfc2 = os.path.join(surveyData, "Stations")
jStaz = arcpy.conversion.ExportFeatures(staJoin, outfc2)
arcpy.Delete_management([outfc, staSumm])
arcpy.management.CalculateField(jStaz, "CeilingZ", "!MAX_Z!", "PYTHON3")
arcpy.management.CalculateField(jStaz, "FloorZ", "!MIN_Z!", "PYTHON3")
arcpy.management.CalculateField(jStaz, "PassageHeightM", "round(!RANGE_Z!, 1)", "PYTHON3")
arcpy.management.CalculateField(jStaz, "PassageHeightFt", "round((!RANGE_Z!*3.28084), 1)", "PYTHON3")
arcpy.management.DeleteField(jStaz, ["FromSta", "OBJECTID_1", "FromSta_1", "COUNT", "COUNT_Z",
                                     "MEAN_Z", "MIN_Z", "MAX_Z", "RANGE_Z"])

#Generate 3D passage model
#This process can take a long time to run
if go3D == "Yes":
        print("Generating 3D passage models")
        #This variation uses the splays intersecting each leg shot
        #The model typically overexaggerates the cave by cutting off sharp bends
        caveModel = arcpy.management.CreateFeatureclass(sVols, "CaveModel", "MULTIPATCH")
        arcpy.AddField_management(legOnly, "LegID", "TEXT")
        arcpy.management.CalculateField(legOnly, "LegID", '"L"+str(!OBJECTID!)', "PYTHON3")
        arcpy.analysis.SplitByAttributes(legOnly, tLegs, 'LegID')
        legList = arcpy.ListFeatureClasses("", "", "TempLegs")
        arcpy.MakeFeatureLayer_management(splays, "splaysLYR")
        for leg in legList:
                arcpy.SelectLayerByLocation_management("splaysLYR", "INTERSECT_3D", leg)
                selVol = arcpy.MinimumBoundingVolume_3d("splaysLYR",'Shape.Z', "VolChunk", "CONVEX_HULL", "ALL")
                arcpy.Append_management(selVol, caveModel, "NO_TEST")
        del leg, legList
        #This variation uses the splays intersecting each station
        #The model typically looks choppy since splays do not overlap enough
        mergePath = fr"{sVols}\CaveModel_FromSplaysOnly"
        arcpy.MinimumBoundingVolume_3d(dissolvedPnts, 'Shape.Z', mergePath, "CONVEX_HULL", "LIST", "StaInt")
        arcpy.Delete_management(selVol)
        #Clean up working files
arcpy.Delete_management([tPnts, tSplays, tLegs, splays, longSC, legOnly])

#Create profile survey, ceiling, and floor lines
#This section is not often used anymore.
if createProfile == "Yes":
    print("Generating Profile Survey, Ceiling, and Floor Lines")
    arcpy.CreateFeatureDataset_management(fileGDB, "Profile", crs)
    ProfileFD = os.path.join(fileGDB, "Profile")
    arcpy.env.workspace = ProfileFD
    #Generate the profile survey stations and line
    ProSurveyPnts_Event = arcpy.MakeXYEventLayer_management(textfile, "Pro_X", "Pro_Y", "Points_SurveyProfile", crs)
    ProSurveyPnts = arcpy.FeatureClassToFeatureClass_conversion(ProSurveyPnts_Event, ProfileFD, "ProfileSurveyPoints")
    ProLn = arcpy.PointsToLine_management(ProSurveyPnts, "ProfileSurveyLine", "Line", "Sort")

#Create additional features in the geodatabase to be used as templates in map production
if newAppend == "Yes":
    print("Mapping feature classes creation started")
    #Generate domains that will be used in map production
    arcpy.CreateDomain_management(fileGDB, "PointTypes", "Various symbology types for points.", "TEXT", "CODED", "DUPLICATE")
    arcpy.CreateDomain_management(fileGDB, "LineTypes", "Various symbology types for lines.", "TEXT", "CODED", "DUPLICATE")
    arcpy.CreateDomain_management(fileGDB, "PolygonTypes", "Various symbology types for polygons.", "TEXT", "CODED", "DUPLICATE")
    arcpy.CreateDomain_management(fileGDB, "TrueFalse", "A simple true or false domain.", "TEXT", "CODED", "DUPLICATE")
    arcpy.CreateDomain_management(fileGDB, "RotationDegree", "Values which point symbology can be rotated by.", "SHORT", "RANGE")
    arcpy.CreateDomain_management(fileGDB, "ViewOptions", "The view which feature represents.", "TEXT", "CODED", "DUPLICATE")
    domDict1 = {"anchor":"Anchor","archeo":"Archeology","blocks":"Breakdown","clay":"Clay","continuation":"Unknown",
                "danger":"Danger","debris":"Debris","dig":"Dig","entrance":"Datum","guano":"Guano","gypsum":"Gypsum",
                "helictite":"Helictite","label":"Note","moonmilk":"Flowstone","mud":"Mud","paleo":"Paleontology",
                "pebbles":"Pebbles","pillar":"Column","popcorn":"Popcorn","root":"Root","sand":"Sand",
                "soda-straw":"Soda Straw","stalactite":"Stalactite","stalagmite":"Stalagmite","user":"Ceiling Height",
                "water-drop":"Water Drop","drop":"Drop Depth","slope":"Floor Slope","tree":"Tree","tire":"Tire",
                "trash":"Trash","organics":"Organic Debris","above":"Above Datum","below":"Below Datum","airwater":"Air over Water"}
    for code in domDict1:        
        arcpy.AddCodedValueToDomain_management(fileGDB, "PointTypes", code, domDict1[code])
    domDict2 = {"border":"Border","ceiling-meander":"Ceiling Channel","chimney":"Ceiling Drop","floor-meander":"Floor Channel"
                ,"pit":"Floor Drop","rock-border":"Rock","slope":"Floor Slope","user":"Other","wall":"Wall",
                "wall blocks":"Breakdown Wall","wall presumed":"Approximate Wall","wall clay":"Clay Wall","water-flow":"Flowing Water",
                "water-int":"Intermittent Water","section":"XS Location","lower":"Lower Level","upper":"Upper Level"}
    for code in domDict2:        
        arcpy.AddCodedValueToDomain_management(fileGDB, "LineTypes", code, domDict2[code])
    domDict3 = {"blocks":"Rock","clay":"Clay Floor","debris":"Organic Debris","pebbles":"Gravel","sand":"Sand Floor",
                "water":"Water Pool","outline":"Cave Outline","pillar":"Pillar","formation":"Formation"}
    for code in domDict3:        
        arcpy.AddCodedValueToDomain_management(fileGDB, "PolygonTypes", code, domDict3[code])
    domDict4 = {"1":"True", "0":"False"}
    for code in domDict4:
        arcpy.AddCodedValueToDomain_management(fileGDB, "TrueFalse", code, domDict4[code])
    domDict5 = {"Plan":"Plan", "Profile":"Profile", "Section":"Section"}
    for code in domDict5:
        arcpy.AddCodedValueToDomain_management(fileGDB, "ViewOptions", code, domDict5[code])
    arcpy.SetValueForRangeDomain_management(fileGDB, "RotationDegree", 0, 359)
    #Generate cave feature templates to be used in map production
    arcpy.CreateFeatureDataset_management(fileGDB, "CaveFeatures", crs)
    caveFeat = os.path.join(fileGDB, "CaveFeatures")
    #Generate point, line, and polygon feature classes which will hold map features
    caveFeatPoints = arcpy.CreateFeatureclass_management(caveFeat, "Points", "POINT")
    arcpy.AddField_management(caveFeatPoints, "PointType", "TEXT", "", "", "50", "Point Type", "", "", "PointTypes")
    arcpy.AddField_management(caveFeatPoints, "Rotation", "SHORT")
    arcpy.AddField_management(caveFeatPoints, "Label", "TEXT", "", "", "50")
    arcpy.AddField_management(caveFeatPoints, "Level", "SHORT", "", "", "", "", "", "", "RotationDegree")
    arcpy.AddField_management(caveFeatPoints, "Shown", "TEXT", "", "", "5", "", "", "", "TrueFalse")
    arcpy.AddField_management(caveFeatPoints, "View", "TEXT", "", "", "10", "", "", "", "ViewOptions")
    caveFeatLines = arcpy.CreateFeatureclass_management(caveFeat, "Lines", "POLYLINE")
    arcpy.AddField_management(caveFeatLines, "LineType", "TEXT", "", "", "50", "Line Type", "", "", "LineTypes")
    arcpy.AddField_management(caveFeatLines, "Level", "SHORT")
    #arcpy.AddField_management(caveFeatLines, "Label", "TEXT", "", "", "50")
    arcpy.AddField_management(caveFeatLines, "Shown", "TEXT", "", "", "5", "", "", "", "TrueFalse")
    arcpy.AddField_management(caveFeatLines, "View", "TEXT", "", "", "10", "", "", "", "ViewOptions")
    #caveFeatLines = arcpy.CreateFeatureclass_management(caveFeat, "CenterLine", "POLYLINE")
    caveOutline = arcpy.CreateFeatureclass_management(caveFeat, "CaveOutline", "POLYGON")
    arcpy.AddField_management(caveOutline, "Level", "SHORT")
    arcpy.AddField_management(caveOutline, "Shown", "TEXT", "", "", "5", "", "", "", "TrueFalse")
    arcpy.AddField_management(caveOutline, "View", "TEXT", "", "", "10", "", "", "", "ViewOptions")
    caveFeatPolygons = arcpy.CreateFeatureclass_management(caveFeat, "Polygons", "POLYGON")
    arcpy.AddField_management(caveFeatPolygons, "PolygonType", "TEXT", "", "", "50", "Polygon Type", "", "", "PolygonTypes")
    arcpy.AddField_management(caveFeatPolygons, "Level", "SHORT")
    arcpy.AddField_management(caveFeatPolygons, "Shown", "TEXT", "", "", "5", "", "", "", "TrueFalse")
    arcpy.AddField_management(caveFeatPolygons, "View", "TEXT", "", "", "10", "", "", "", "ViewOptions")
    print("Mapping feature classes creation completed")
    #Create leads layer
    if createLeads == "Yes":
        print("Generating Leads feature class")
        arcpy.CreateDomain_management(fileGDB, "LeadStatus", "Options for the status of a lead.", "TEXT", "CODED", "DUPLICATE")
        domDict5 = {"Open":"Open", "Resolved":"Resolved"}
        for code in domDict5:
            arcpy.AddCodedValueToDomain_management(fileGDB, "LeadStatus", code, domDict5[code])
        caveFeatLeads = arcpy.CreateFeatureclass_management(caveFeat, "Leads", "POINT")
        arcpy.AddField_management(caveFeatLeads, "ID_Num", "SHORT", "", "", "", "ID Number")
        arcpy.AddField_management(caveFeatLeads, "Level", "SHORT")
        arcpy.AddField_management(caveFeatLeads, "US_Station", "TEXT", "", "", "50", "US Station")
        arcpy.AddField_management(caveFeatLeads, "DS_Station", "TEXT", "", "", "50", "DS Station")
        arcpy.AddField_management(caveFeatLeads, "TieIn", "TEXT", "", "", "50", "Tie In Station")
        arcpy.AddField_management(caveFeatLeads, "Area", "TEXT", "", "", "150")
        arcpy.AddField_management(caveFeatLeads, "Comment", "TEXT", "", "", "254")
        arcpy.AddField_management(caveFeatLeads, "Status", "TEXT", "", "", "50", "", "", "", "LeadStatus")
        print("Leads feature class creation completed")

print("Processing completed, hope things go well moving forward.")

print("Processing completed, hope things go well moving forward.")
