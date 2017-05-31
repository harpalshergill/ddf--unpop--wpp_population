import pandas as pd
import numpy as np
import re
import os
from ddf_utils.str import to_concept_id
from ddf_utils.index import create_datapackage

source_migration = '../source/WPP2015_MIGR_F02_NET_NUMBER_OF_MIGRANTS.XLS'
out_dir = '../../'

def load_files_Migration(source):
    data_est = pd.read_excel(source, sheetname='ESTIMATES', skiprows=16, na_values='…')
    data_varM = pd.read_excel(source, sheetname='MEDIUM VARIANT', skiprows=16, na_values='…')
    
    data_est = cleanup_data_For_Migration(data_est)
    data_varM = cleanup_data_For_Migration(data_varM)
    
    return [data_est, data_varM]


def cleanup_data_For_Migration(data):
    #remove index and Notes column
    data = data.drop(['Index', 'Notes'], axis=1)
    
    #rename country column and country code column
    data = data.rename(columns={
        'Major area, region, country or area *': 'Ref_Area',
        'Country code': 'Ref_Area_Code'
    })
    
    return data

def extract_entities_5yearInterval(data_est):
    """extract ages from estimates tab of source data."""

    df = pd.DataFrame([], columns=['five_year_interval'])
    df['five_year_interval'] = data_est.columns[5:]
    df['five_year_interval'] = df['five_year_interval'].str.replace('-', '_')

    #print(df.head(10))
    #df['age_name'] = 'Age ' + df['age']
    return df

def extract_datapoint_Migration(dflist):
    to_concat = []
    
    for df in dflist:
        e = df.drop(['Ref_Area'], axis = 1)
        e = e.set_index(['Ref_Area_Code', 'Variant'])
        e.columns.name = 'five_year_interval'
        df_new = e.stack().reset_index().rename(columns={0: 'populationmigration'})
        to_concat.append(df_new)
        
    df_all = pd.concat(to_concat, ignore_index = True)

    #data  = df_all.FiveYearInterval.str[:4]
    df_all.insert(1, 'year', df_all.five_year_interval.str[:4])

    #print(df_all.head(10))

    df_all.columns = list(map(to_concept_id, df_all.columns))
    
    df_all['year'] = df_all['year'].astype('category', categories=list(df_all['year'].unique()), ordered = True)
    
    df_all = df_all.sort_values(by = ['ref_area_code', 'year', 'variant'])
    return df_all

def generate_Population_Migration_Data(source):
    print('reading TotalPop source data with Variance...')
    print('\Both Sex...')
    df_bothSex = load_files_Migration(source)
    
    print('Extracting DataPoints...')
    df_bothSex_DP = extract_datapoint_Migration(df_bothSex)
    
    for geo, idxs in df_bothSex_DP.groupby(by='ref_area_code').groups.items():
        path = os.path.join(out_dir, 
            'ddf--datapoints--populationmigration--by--ref_area_code--year--five_year_interval--variant.csv/ddf--datapoints--populationmigration--by--ref_area_code-{}--year--five_year_interval--variant.csv'.format(geo))
        to_save = df_bothSex_DP.ix[idxs]
        
        
        to_save = to_save.sort_values(by=['ref_area_code', 'year'])
        if(geo == 900):
            #print('{0:f}'.format(to_save.populationmigration))
            to_save.ix[idxs].to_csv(path, index=False, float_format='%.4f')
        else:
            to_save.ix[idxs].to_csv(path, index=False, float_format='%.15g')
    
    
    #get the 5year interval to csv
    Five_yr_int = extract_entities_5yearInterval(df_bothSex[0])
    path = os.path.join(out_dir, 'ddf--entities--five_year_interval.csv')
    Five_yr_int.to_csv(path, index=False)

def main():
    generate_Population_Migration_Data(source_migration)

if __name__ =='__main__':
    main()