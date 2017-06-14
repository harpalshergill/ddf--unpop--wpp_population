
# coding: utf-8

# In[1]:

import pandas as pd
import numpy as np
from openpyxl import load_workbook
#from xlrd import open_workbook
import re
import os
import time
from os import listdir
from os.path import isfile, join
from ddf_utils.str import to_concept_id
from ddf_utils.index import create_datapackage


# In[38]:

out_dir = '../../'
#out_dir = '../'

# global variables to build data for concepts and entities
variants = []
agegroups = []
age1YrInterval = []
ageBroad = []
age5YrInterval = []
ref_AreaCode = []


# In[3]:

#method to read files in a folder...
#onlyfiles = [f for f in listdir('source/byYearInterval') if isfile(join('source/byYearInterval', f))]
#onlyfiles


# In[4]:

# method to create directory if it does not exist
def createDirectory(Directory):
    if not os.path.exists('../'+Directory.lower()):
        os.makedirs('../'+Directory.lower())


# In[5]:

# method to generate files from the data points.
def GenerateYearFormatFiles(ds_all, Directory, FileNameWithPath, gender, Ref_Area_List):
    # drop gender column is both sex or NA.
    if (gender.upper() == 'TOTAL') or (gender.upper() == "NA"):
        ds_all = ds_all.drop('gender', axis=1)

    # group data by ref_area_code as files are generated by this grouping
    for geo, idxs in ds_all.groupby(by='ref_area_code').groups.items():
        myDS = ds_all.ix[idxs]
        #change the age dimenstion based on age group in file
        if("agebroad" in Directory.lower()):
            myDS = myDS.rename(columns={
                'age': 'agebroad'
            })
        elif("age1yearinterval" in Directory.lower()):
            myDS = myDS.rename(columns={
                'age': 'age1yearinterval'
            })
        elif("age5yearinterval" in Directory.lower()):
            myDS = myDS.rename(columns={
                'age': 'age5yearinterval'
            })
        
        
        data = Ref_Area_List.loc[Ref_Area_List['Code'] == geo]
        # update the directory and file names based on geo in country, continent, region or global
        if(data.iloc[0]['is--world'] == 1):
            NewDirectory = Directory.replace('ref_area_code','global')
            NewFileNameWithPath = FileNameWithPath.replace('ref_area_code','global')
            myDS = myDS.rename(columns={
                'ref_area_code': 'global'
            })
        elif (data.iloc[0]['is--region'] == 1):
            NewDirectory = Directory.replace('ref_area_code','region')
            NewFileNameWithPath = FileNameWithPath.replace('ref_area_code','region')
            myDS = myDS.rename(columns={
                'ref_area_code': 'region'
            })
        elif (data.iloc[0]['is--continent'] == 1):
            NewDirectory = Directory.replace('ref_area_code','continent')
            NewFileNameWithPath = FileNameWithPath.replace('ref_area_code','continent')
            myDS = myDS.rename(columns={
                'ref_area_code': 'continent'
            })
        elif (data.iloc[0]['is--country'] == 1):
            NewDirectory = Directory.replace('ref_area_code','country')
            NewFileNameWithPath = FileNameWithPath.replace('ref_area_code','country')
            myDS = myDS.rename(columns={
                'ref_area_code': 'country'
            })
        
        createDirectory(NewDirectory)
        path = os.path.join(out_dir,NewDirectory+'/'+NewFileNameWithPath.format(geo))
        
        myDS.to_csv(path, index=False, float_format='%.15g')


# In[6]:

# method to load files, skip the first 16 lines and specify na values as '...'
def load_Files(source, variant, gender, TypeBy):
    #load file using pandas
    data = pd.read_excel(source, sheetname= variant, skiprows=16, na_values='…')
    data = data.drop(['Index', 'Notes'], axis = 1)
    
    #remove the empty space and convert '-' to '_' char
    data['Variant'] = data['Variant'].str.lower().replace(' ', '').replace('-','')
    
    #rename country column and country code column
    data = data.rename(columns={
        'Major area, region, country or area *': 'Ref_Area',
        'Country code': 'Ref_Area_Code'
    })
    #year column is present in Age Type sheets
    if (TypeBy == "Age"):
        data = data.rename(columns={
        'Reference date (as of 1 July)': 'Year'
    })
    #insert Gender column
    data.insert(3, 'Gender', gender)
    if (TypeBy == "YearInterval"):
        data.insert(3, 'Freq', '5yearly')
    elif (TypeBy == "AgeYearInterval"):
        data = data.rename(columns={
        'Period': 'Year'
        })
        #get first year in yyyy-yyyy time period
        data['Year'] = data['Year'].str[:4] 
        data.insert(3, 'Freq', '5yearly')

    #update teh AreaCode entity list
    global ref_AreaCode
    ref_AreaCode = ref_AreaCode + list(set(data['Ref_Area_Code']) - set(ref_AreaCode))

    return data
    


# In[7]:

def GetDataFromWorkBookSheets(source, gender, indicator, TypeBy):
    all_variants = []

    #pandas excel file fun.
    wbb = pd.ExcelFile(source)
    
    #add variant concepts to global variable for entity set
    global variants
    variants = variants + list(set(wbb.sheet_names) - set(variants))
    
    #iterate through each SHEET except "NOTES"
    for sheetName in wbb.sheet_names:
        if(sheetName == 'NOTES'):
            #ignore NOTES sheet since we are not collecting metadata yet
            continue
        else:
            #first load the files
            mydata = load_Files(source, sheetName, gender, TypeBy)
            mydata = mydata.drop(['Ref_Area'], axis=1)
            #based on File format type apply the index and set the column value
            if (TypeBy == "Age"):
                mydata = mydata.set_index(['Ref_Area_Code','Year','Variant','Gender'])
                mydata.columns.name = 'Age'
            elif (TypeBy == "Year"):
                mydata = mydata.set_index(['Ref_Area_Code','Variant', 'Gender'])
                mydata.columns.name = 'Year'
            elif (TypeBy == "YearInterval"):
                mydata = mydata.set_index(['Ref_Area_Code','Variant', 'Gender', 'Freq'])
                mydata.columns.name = 'Year'
            elif (TypeBy == "AgeYearInterval"):
                mydata = mydata.set_index(['Ref_Area_Code','Year','Variant','Gender', 'Freq'])
                mydata.columns.name = 'Age'
            
            mydata = mydata.stack().reset_index().rename(columns={0:indicator})
            all_variants.append(mydata)
            
            #break
    return all_variants


# In[30]:

#method to sort the file with refArea, Year, Variant, Gender
def sortDataSets(dsSet_all, TypeBy, FileName):
    dataSet = pd.concat(dsSet_all, ignore_index=True) 
    dataSet.columns = list(map(to_concept_id, dataSet.columns))
    
    #remove the blank space from variants
    dataSet['variant'] = [ x.replace(' ', '').replace('-','') for x in dataSet['variant']]
        
    #global agegroups
    global age1YrInterval
    global ageBroad
    global age5YrInterval
    
    if (TypeBy == "Age"): 
        #update the global variables for 3 age groups with any new values
        if("broad_age" in FileName.lower()):
            ageBroad = ageBroad + list(set(dataSet['age'].unique()) - set(ageBroad))
        elif("age_annual" in FileName.lower()):
            age1YrInterval = age1YrInterval + list(set(dataSet['age'].unique()) - set(age1YrInterval))
        elif("_age_" in FileName.lower()):
            age5YrInterval = age5YrInterval + list(set(dataSet['age'].unique()) - set(age5YrInterval))
        #replace - and + and higher case char to _, plus and lower case respectively
        dataSet['age'] = [ x.replace('-','_').replace('+','plus').replace('Total','total').strip() for x in dataSet['age']]
        
        dataSet['age'] = dataSet['age'].astype('category', categories=list(dataSet['age'].unique()), ordered=True)
        dataSet = dataSet.sort_values(by=['ref_area_code', 'year','age','variant', 'gender'])
    elif (TypeBy == "Year"):
        dataSet = dataSet.sort_values(by=['ref_area_code', 'year','variant', 'gender'])
    elif (TypeBy == "YearInterval"):
        dataSet['year'] = dataSet['year'].str[:4]
        dataSet = dataSet.sort_values(by=['ref_area_code', 'year','variant', 'gender', 'freq'])
    elif (TypeBy == "AgeYearInterval"):
        #update the global variables for 3 age groups with any new values
        if("broad_age" in FileName.lower()):
            ageBroad = ageBroad + list(set(dataSet['age'].unique()) - set(ageBroad))
        elif("age_annual" in FileName.lower()):
            age1YrInterval = age1YrInterval + list(set(dataSet['age'].unique()) - set(age1YrInterval))
        elif("_age_" in FileName.lower()):
            age5YrInterval = age5YrInterval + list(set(dataSet['age'].unique()) - set(age5YrInterval))
        dataSet['age'] = [ x.replace('-','_').replace('+','plus').replace('Total','total').strip() for x in dataSet['age']]
        
        dataSet['age'] = dataSet['age'].astype('category', categories=list(dataSet['age'].unique()), ordered=True)
        dataSet = dataSet.sort_values(by=['ref_area_code', 'year','age','variant', 'gender', 'freq'])
   
    return dataSet


# In[31]:

# hardcode the indicator's Note and Descriptions values for indicators which shares multiple files. 
def updateConceptDF(df, myDSvals, Indicator):
    if(Indicator.lower() == "population"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'population by age group (thousands)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'population by age group, major area, region and country, 1950-2100 (thousands)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "lifeexpectancy"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'life expectancy, e(x), at exact age x (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'life expectancy at exact age, e(x), by major area, region and country, 1950-2100'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "lifeexpectancyat15"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'life expectancy at age 15 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'life expectancy at age 15 by major area, region and country, 1950-2100 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "lifeexpectancyat60"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'life expectancy at age 60 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'life expectancy at age 60 by major area, region and country, 1950-2100 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "lifeexpectancyat80"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'life expectancy at age 80 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'life expectancy at age 80 by major area, region and country, 1950-2100 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "lifeexpectancyatbirth"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'life expectancy at birth (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'life expectancy at birth by major area, region and country, 1950-2100 (years)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "mortality15to50per1000aliveat15"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'adult mortality between age 15 and 50, 35q15 (deaths under age 50 per 1,000 alive at age 15)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'probability of dying between the ages of 15 and 50 years by major area, region and country, 1950-2100 (deaths under age 50 per 1,000 alive at age 15)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "mortality15to60per1000aliveat15"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'adult mortality between age 15 and 60, 45q15 (deaths under age 60 per 1,000 alive at age 15)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'probability of dying between the ages of 15 and 60 years by major area, region and country, 1950-2100 (deaths under age 60 per 1,000 alive at age 15)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "percentagetotaldeaths"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'Percentage of deaths by age group (per 100 (male/female/all) total population)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'Percentage of deaths by age group, major area, region and country, 1950-2100'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "percentagetotalpopulation"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'Percentage of population by age group (per 100 (male/female/all) total population)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'Percentage population by age group, major area, region and country, 1950-2100'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "sexratio_maleper100female"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'Sex ratio by age group (males per 100 females by age group)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'Sex ratio by age group, major area, region and country, 1950-2100 (males per 100 females by age group)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "survivorage"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'life table survivors, l(x), at exact age (x)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'life table survivors at exact age, l(x), by major area, region and country, 1950-2100'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "totaldeaths"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'Number of deaths (thousands)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'deaths, by major area, region and country, 1950-2100 (thousands)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "under40mortalityper1000livebirth"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'under-forty mortality, 40q0 (deaths under age 40 per 1,000 live births)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'probability of dying between birth and the age of 40 years by major area, region and country, 1950-2100 (deaths under age 40 per 1,000 live births)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    elif(Indicator.lower() == "under60mortalityper1000livebirth"):
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = 'under-sixty mortality, 60q0 (deaths under age 60 per 1,000 live births)'
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = 'probability of dying between birth and the age of 60 years by major area, region and country, 1950-2100 (deaths under age 60 per 1,000 live births)'
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    else:
        df.loc[(df['concept'] == Indicator.lower()), 'name'] = myDSvals[1].iloc[6]
        df.loc[(df['concept'] == Indicator.lower()), 'description'] = myDSvals[0].iloc[0]
        df.loc[(df['concept'] == Indicator.lower()), 'sourceurl'] = 'https://esa.un.org/unpd/wpp/DVD/'
    return df


# In[32]:

#method to have concept dataframe updated with note and descriptions for each measure.
def updateMetaData(df, TypeBY, Directory, FileName, Indicator):
    if(";" in FileName):
        #then get first filename
        files = FileName.split(";")
        FileName = files[0]
    
    #read the excel file to get indicator and description
    if(TypeBY == 'Age'or TypeBY == "AgeYearInterval"):
        myDSvals = pd.read_excel("source/"+FileName, sheetname='ESTIMATES', skiprows=9, nrows=16 ,  header=None, parse_cols = "A,G")
        df = updateConceptDF(df, myDSvals, Indicator)
    else:
        myDSvals = pd.read_excel("source/"+FileName, sheetname='ESTIMATES', skiprows=9, nrows=16 ,  header=None, parse_cols = "A,F")
        df = updateConceptDF(df, myDSvals, Indicator)
    return df


# In[33]:

#MAIN Function. Calls the metadata.xslx file and iterate through each file
#supports reading multiple files and concatenating them to one dataset as well.
def callDataPointFiles(metadata_df, cdf):
    Ref_Area_List = pd.read_excel('source/countrymetadata.xlsx', parse_cols = "A:G")
    df = metadata_df
    MainStart = time.time()
    for i, row in enumerate(metadata_df.values):
        start = time.time()
        
        #date = metadata_df.index[i]
        FileName, TypeBY, SEX, Indicator, Directory, name, description, url = row
        newFileName = Directory.lower()
        newFileName = newFileName.replace("ref_area_code", "ref_area_code-{}")
        newFileName = newFileName + ".csv"

        #if (Indicator.lower() == "feminityratio_femaleper100male"):
        if (TypeBY == "Year" or TypeBY == "Age" or TypeBY == "YearInterval" or TypeBY == "AgeYearInterval"):
            print( str(i+1) + ' of '+ str(metadata_df.shape[0]) +' -- ' + FileName)
            
            #update concept name & description in metadata file
            #at the moment same file is being read twice(once for note and desc and then for main dataset)
            #this could be made more efficient by reading file only once
            cdf = updateMetaData(cdf, TypeBY, Directory, FileName, Indicator)
            
            #check if FileName has two or more files. for ex same dimensions with male and female
            if(";" in FileName):
                #if yes then run the method for each files and merge the two dataset.
                files = FileName.split(";")
                ds_allSex = []
                #iterate through files then
                for file in files:
                    if "_MALE" in file:
                        SEX = "male"
                    elif "_FEMALE" in file:
                        SEX = "female"
                    ds_sex = GetDataFromWorkBookSheets("source/"+file, SEX, Indicator, TypeBY) 
                    ds_allSex.append(ds_sex)
                    
                #concat all the sheets and files together as one list
                mainds = []
                for dss in ds_allSex:
                    for dss1 in dss:
                        mainds.append(dss1)
                dataSet = sortDataSets(mainds, TypeBY, FileName)
            else:
                ds_sex = GetDataFromWorkBookSheets("source/"+FileName, SEX, Indicator, TypeBY) 
                dataSet = sortDataSets(ds_sex, TypeBY, FileName)
                
            dataSet = dataSet.drop_duplicates()

            #create files from dataset
            GenerateYearFormatFiles(dataSet, Directory.lower(), newFileName, SEX, Ref_Area_List)
            
            end = time.time()            
            print ('Time Taken: ' + str(end-start)) 
            #break
    FinalEnd = time.time()
    print ('Total Time For All Files: ' + str(FinalEnd-MainStart))
    return cdf


# In[34]:

# all functions here are to generate the concepts and entities files.
def generateEntities_Gender():
    cdf = pd.DataFrame([], columns=['gender'])
    cdf['gender'] = ['male', 'female']
    
    path = os.path.join(out_dir, 'ddf--entities--gender.csv')
    cdf.to_csv(path, index=False)

def generateEntities_Freq():
    cdf = pd.DataFrame([], columns=['freq'])
    cdf['freq'] = ['5yearly']
    
    path = os.path.join(out_dir, 'ddf--entities--freq.csv')
    cdf.to_csv(path, index=False)
def generateEntities_Variant():
    variant = [x.lower().replace(' ', '').replace('-', '') for x in variants if x != 'NOTES']
    
    cdf = pd.DataFrame([], columns=['variant'])
    cdf['variant'] = variant
    
    path = os.path.join(out_dir, 'ddf--entities--variant.csv')
    cdf.to_csv(path, index=False)
def generateEntities_AgeGroups():
    cdf = pd.DataFrame([], columns=['agebroad','is--agebroad'])
    cdf['agebroad'] = [ x.replace('-','_').replace('+','plus').replace('Total','total').strip() for x in sorted(set(ageBroad))]
    cdf['is--agebroad'] = 'TRUE'    
    path = os.path.join(out_dir, 'ddf--entities--age--agebroad.csv')
    cdf.to_csv(path, index=False)
    
    cdf1 = pd.DataFrame([], columns=['age1yearinterval','is--age1yearinterval'])
    #print(age1YrInterval)
    cdf1['age1yearinterval'] = [ x.replace('-','_').replace('+','plus').replace('Total','total').strip() for x in sorted(set(age1YrInterval))]
    cdf1['is--age1yearinterval'] = 'TRUE'    
    path = os.path.join(out_dir, 'ddf--entities--age--age1yearinterval.csv')
    cdf1.to_csv(path, index=False)
    
    cdf2 = pd.DataFrame([], columns=['age5yearinterval','is--age5yearinterval'])
    cdf2['age5yearinterval'] = [ x.replace('-','_').replace('+','plus').replace('Total','total').strip() for x in sorted(set(age5YrInterval))]
    cdf2['is--age5yearinterval'] = 'TRUE'    
    path = os.path.join(out_dir, 'ddf--entities--age--age5yearinterval.csv')
    cdf2.to_csv(path, index=False)

    
def generateEntities_RefAreaCode():
    Ref_Area_List = pd.read_excel('source/countrymetadata.xlsx', parse_cols = "A:G")
    
    cdf = pd.DataFrame([], columns=['country', 'name','is--country', 'parent'])
    cdf['country'] = Ref_Area_List.loc[Ref_Area_List['is--country'] == 1, 'Code']
    cdf['name'] = Ref_Area_List.loc[Ref_Area_List['is--country'] == 1, 'Region']
    cdf['parent'] = Ref_Area_List.loc[Ref_Area_List['is--country'] == 1, 'Parent']
    cdf['is--country'] = 'TRUE'    
    path = os.path.join(out_dir, 'ddf--entities--geo--country.csv')
    cdf.to_csv(path, index=False)
    
    cdf1 = pd.DataFrame([], columns=['region','name','is--region','parent'])
    cdf1['region'] = Ref_Area_List.loc[Ref_Area_List['is--region'] == 1, 'Code']
    cdf1['name'] = Ref_Area_List.loc[Ref_Area_List['is--region'] == 1, 'Region']
    cdf1['parent'] = Ref_Area_List.loc[Ref_Area_List['is--region'] == 1, 'Parent']
    cdf1['is--region'] = 'TRUE'
    path = os.path.join(out_dir, 'ddf--entities--geo--region.csv')
    cdf1.to_csv(path, index=False)
    
    cdf2 = pd.DataFrame([], columns=['continent','name','is--continent','parent'])
    cdf2['continent'] = Ref_Area_List.loc[Ref_Area_List['is--continent'] == 1, 'Code']
    cdf2['name'] = Ref_Area_List.loc[Ref_Area_List['is--continent'] == 1, 'Region']
    cdf2['parent'] = Ref_Area_List.loc[Ref_Area_List['is--continent'] == 1, 'Parent']
    cdf2['is--continent'] = 'TRUE'
    path = os.path.join(out_dir, 'ddf--entities--geo--continent.csv')
    cdf2.to_csv(path, index=False)
    
    cdf3 = pd.DataFrame([], columns=['global','name','is--global'])
    cdf3['global'] = Ref_Area_List.loc[Ref_Area_List['is--world'] == 1, 'Code']
    cdf3['name'] = Ref_Area_List.loc[Ref_Area_List['is--world'] == 1, 'Region']
    cdf3['is--global'] = 'TRUE'
    path = os.path.join(out_dir, 'ddf--entities--geo--global.csv')
    cdf3.to_csv(path, index=False)
    
def createConceptsDF(metadata):
    concept_name = ['Year', 'Age', 'Gender', 'Freq','Variant' ,'Geo', 'Country', 
                    'Region', 'Continent', 'Global','AgeBroad', 'Age1YearInterval','Age5YearInterval'
                   ,'name', 'parent', 'domain','description', 'sourceurl']
    
    concept_name = concept_name + list(metadata.Indicator.unique())
    #print(concept_name)
    
    # 53 print(len(list(metadata.Indicator.unique())))
    
    concepts = list(map(to_concept_id, concept_name))
    cdf = pd.DataFrame([], columns=['concept', 'concept_type', 'domain', 'name', 'description', 'sourceurl'])
    cdf['concept'] = concepts
    cdf['concept_type'] = 'measure'
    cdf['concept_type'].iloc[1:6] = 'entity_domain'
    cdf['concept_type'].iloc[6:13] = 'entity_set'
    cdf['concept_type'].iloc[13:18] = 'string'
    cdf['domain'].iloc[6:10] = 'geo'
    cdf['domain'].iloc[10:13] = 'age'
    cdf['concept_type'].iloc[0] = 'time'
    
    return cdf
    
def generateConcepts(cdf):
    path = os.path.join(out_dir, 'ddf--concepts.csv')
    cdf.to_csv(path, index=False)
    


# In[37]:

metadata_df = pd.read_excel('source/metadata.xlsx', parse_cols = "A:E")
metadata_df['name'] = ''
metadata_df['description'] = ''
metadata_df['sourceurl'] = 'https://esa.un.org/unpd/wpp/Download/Standard/Population/'

#createConceptDF
cdf = createConceptsDF(metadata_df)
#print (metadata_df)
cdf = callDataPointFiles(metadata_df, cdf)
#print (metadata_df)
#generate concepts
generateConcepts(cdf)

#generate variants
generateEntities_Variant()

#generate countries/world/regions
generateEntities_RefAreaCode()

#generate age groups
generateEntities_AgeGroups()

#generate gender
generateEntities_Gender()

#generate freq
generateEntities_Freq()

#print (concepts)

# add year interval information for freqency/
# split ref_area_code into World/Continent/Region/Country


# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:




# In[ ]:



