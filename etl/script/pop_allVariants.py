import pandas as pd
import numpy as np
import re
import os
from ddf_utils.str import to_concept_id
from ddf_utils.index import create_datapackage

source_t = '../source/WPP2015_POP_F01_1_TOTAL_POPULATION_BOTH_SEXES.XLS'
source_m = '../source/WPP2015_POP_F01_2_TOTAL_POPULATION_MALE.XLS'
source_f = '../source/WPP2015_POP_F01_3_TOTAL_POPULATION_FEMALE.XLS'



out_dir = '../../'

def cleanup_data(data, gender):
    #remove index and Notes column
    data = data.drop(['Index', 'Notes'], axis=1)
    
    #rename country column and country code column
    data = data.rename(columns={
        'Major area, region, country or area *': 'Ref_Area',
        'Country code': 'Ref_Area_Code'
    })
    
    #insert Gender column
    data.insert(3, 'Gender', gender)
    
    return data

def read_cleanup_Age_Annual(source, gender):
	data_est = pd.read_excel(source, sheetname='ESTIMATES', skiprows=16, na_values='…')
	data_var = pd.read_excel(source, sheetname='MEDIUM VARIANT', skiprows=16, na_values='…')

	# rename/drop some columns.
	# for 80+ and 100+ groups, rename to 80plus and 100plus
	data_est = data_est.drop(['Index', 'Notes'], axis=1)
	data_var = data_var.drop(['Index', 'Notes'], axis=1)

	data_est = data_est.rename(columns={
		'Major area, region, country or area *': 'Ref_Area',
		'Country code': 'Ref_Area_Code'
	})

	data_var = data_var.rename(columns={
		'Major area, region, country or area *': 'Ref_Area',
		'Country code': 'Ref_Area_Code'
	})

	data_est = data_est.rename(columns={'80+': '80plus',
	                                    '100+': '100plus'})
	data_var = data_var.rename(columns={'100+': '100plus'})  # todo: no use to rename for now.

	# insert Gender column and rearrange the order
	col_est_1 = data_est.columns[:4]
	col_est_2 = data_est.columns[4:]

	col_var_1 = data_var.columns[:4]
	col_var_2 = data_var.columns[4:]

	cols_est = [*col_est_1, 'Gender', *col_est_2]
	cols_var = [*col_var_1, 'Gender', *col_var_2]

	data_est['Gender'] = gender
	data_var['Gender'] = gender

	return (data_est[cols_est], data_var[cols_var])

def extract_concepts(data_est):
	concept_name = list(data_est.columns[:4])
	concept_name.append('Year')
	concept_name.append('Population')
	concept_name.append('variant_name')
	concept_name.append('Age')
	concept_name.append('name')
	concept_name.append('five_year_interval')
	concept_name.append('populationmigration')


	concepts = list(map(to_concept_id, concept_name))

	# now construct the dataframe
	cdf = pd.DataFrame([], columns=['concept', 'concept_type', 'name'])
	cdf['concept'] = concepts
	cdf['name'] = concept_name

	cdf['concept_type'] = 'string'

	# population
	cdf['concept_type'].iloc[[5,10]] = 'measure'

	# entity domains
	cdf['concept_type'].iloc[[0, 2, 3, 6, 7, 9]] = 'entity_domain'

	# year
	cdf['concept_type'].iloc[4] = 'time'

	return cdf


def extract_entities_country(data_est, data_varM, data_varH, data_varL):
    # extract countires name
    # check if all data set has same numbers of countires
    
    
    data_est.columns = list(map(to_concept_id, data_est.columns))
    data_varM.columns = list(map(to_concept_id, data_varM.columns))
    data_varH.columns = list(map(to_concept_id, data_varH.columns))
    data_varL.columns = list(map(to_concept_id, data_varL.columns))

    entity = data_est[['ref_area', 'ref_area_code']].copy()
    entity = entity.drop_duplicates()
    
    entity2 = data_varM[['ref_area', 'ref_area_code']].copy()
    entity2 = entity2.drop_duplicates()
    
    entity3 = data_varH[['ref_area', 'ref_area_code']].copy()
    entity3 = entity3.drop_duplicates()
    
    entity4 = data_varL[['ref_area', 'ref_area_code']].copy()
    entity4 = entity4.drop_duplicates()
    
    if (len(entity) != len(entity2) or
        len(entity) != len(entity3) or
        len(entity) != len(entity4)):
        print('Warning: entities not same in the excel tabs.')

        ent = pd.concat([entity, entity2, entity3, entity4])
        return ent.drop_duplicates()

    return entity

def extract_entities_gender():
    """no more information about gender in source, just create that"""
    df = pd.DataFrame([], columns=['gender'])
    df['gender'] = ['male', 'female']
    # df['name'] = ['Male', 'Female']

    return df

def extract_entities_variant():
	df = pd.DataFrame([], columns=['variant', 'variant_name'])
	df['variant'] = ['estimate', 'medium', 'high', 'low']
	df['variant_name'] = ['estimates', 'medium_variant', 'high_variant', 'low_variant']

	return df

def extract_entities_age(data_est):
	"""extract ages from estimates tab of source data."""

	df = pd.DataFrame([], columns=['age'])
	df['age'] = data_est.columns[5:]

	#df['age_name'] = 'Age ' + df['age']
	return df

def extract_datapoints_Age_Annual(dflist):
	"""make datapoint file with all dataframe in dflist."""

	to_concat = []

	for df in dflist:
		e = df.drop([ 'Ref_Area'], axis=1)
		e = e.set_index([
			'Ref_Area_Code', 'Reference date (as of 1 July)', 'Gender', 'Variant'])
		e.columns.name = 'Age'
		df_new = e.stack().reset_index().rename(columns={0: 'Population'})
		to_concat.append(df_new)

	df_all = pd.concat(to_concat, ignore_index=True)
	df_all = df_all.rename(columns={'Reference date (as of 1 July)': 'Year'})
	df_all.columns = list(map(to_concept_id, df_all.columns))

	# make age column sort correctly by changing to categorial dtype.
	df_all['age'] = df_all['age'].astype('category', categories=list(df_all['age'].unique()), ordered=True)

	df_all = df_all.sort_values(by=['ref_area_code', 'year', 'age', 'gender', 'variant'])

	# the only duplicates are in year 2015. There are both esitmated and observed data.
	# But both are same so we can drop them.
	# df_all = df_all.drop_duplicates()
	# assert not np.any(df_all.duplicated(['country_code', 'year', 'age', 'gender']))

	return df_all

def extract_datapoints(dflist):
    to_concat = []
    
    for df in dflist:
        e = df.drop(['Ref_Area'], axis=1)
        e = e.set_index(['Ref_Area_Code','Variant', 'Gender'])
        e.columns.name = 'Year'
        dfnew = e.stack().reset_index().rename(columns={0:'Population'})
        to_concat.append(dfnew)
        
    df_all = pd.concat(to_concat, ignore_index=True)

    df_all.columns = list(map(to_concept_id, df_all.columns))
    #since year does not contain characters like age does...
    #df_all['year'] = df_all['year'].astype('category', categories=list(df_all['year'].unique()), ordered=True)
    df_all = df_all.sort_values(by=['ref_area_code', 'year','variant', 'gender'])

    return df_all

def load_files(source, gender):
    data_est = pd.read_excel(source, sheetname='ESTIMATES', skiprows=16, na_values='…')
    data_varM = pd.read_excel(source, sheetname='MEDIUM VARIANT', skiprows=16, na_values='…')
    data_varH = pd.read_excel(source, sheetname='HIGH VARIANT', skiprows=16, na_values='…')
    data_varL = pd.read_excel(source, sheetname='LOW VARIANT', skiprows=16, na_values='…')
    
    data_est = cleanup_data(data_est, gender)
    data_varM = cleanup_data(data_varM, gender)
    data_varH = cleanup_data(data_varH, gender)
    data_varL = cleanup_data(data_varL, gender)
    
    return [data_est, data_varM, data_varH, data_varL]

def generate_Population_Age_Annual_Data():

	source_t = '../source/WPP2015_INT_F03_1_POPULATION_BY_AGE_ANNUAL_BOTH_SEXES.XLS'
	source_m = '../source/WPP2015_INT_F03_2_POPULATION_BY_AGE_ANNUAL_MALE.XLS'
	source_f = '../source/WPP2015_INT_F03_3_POPULATION_BY_AGE_ANNUAL_FEMALE.XLS'

	print('reading Population with Annual source data...')
	print('\tboth sexes...')
	est_t, var_t = read_cleanup_Age_Annual(source_t, 'both_sexes')
	print('\tmale...')
	est_m, var_m = read_cleanup_Age_Annual(source_m, 'male')
	print('\tfemale...')
	est_f, var_f = read_cleanup_Age_Annual(source_f, 'female')

	print('creating datapoint file...')
	dflist = [est_m, var_m, est_f, var_f]
	df_mf = extract_datapoints_Age_Annual(dflist)
	for geo, idxs in df_mf.groupby(by='ref_area_code').groups.items():
		path = os.path.join(out_dir, 
			'ddf--datapoints--population--by--ref_area_code--year--gender--age--variant/ddf--datapoints--population--by--ref_area_code-{}--year--gender--age--variant.csv'.format(geo))
		to_save = df_mf.ix[idxs]
		to_save = to_save.sort_values(by=['ref_area_code', 'year'])
		to_save.ix[idxs].to_csv(path, index=False, float_format='%.15g')

	df_t = extract_datapoints_Age_Annual([est_t, var_t])
	df_t = df_t.drop('gender', axis=1)  # we don't need gender = both sexes in datapoint
	for geo, idxs in df_t.groupby(by='ref_area_code').groups.items():
		path = os.path.join(out_dir, 
			'ddf--datapoints--population--by--ref_area_code--year--age--variant/ddf--datapoints--population--by--ref_area_code-{}--year--age--variant.csv'.format(geo))
		to_save = df_t.ix[idxs]
		to_save = to_save.sort_values(by=['ref_area_code', 'year'])
		to_save.ix[idxs].to_csv(path, index=False, float_format='%.15g')

	age = extract_entities_age(est_t)
	path = os.path.join(out_dir, 'ddf--entities--age.csv')
	age.to_csv(path, index=False)

def generate_Population_Variance_Data():
	print('reading TotalPop source data with Variance...')
	print('\Both Sex...')
	df_bothSex = load_files(source_t, 'both_sexes')
	print('\tFemale...')
	df_female = load_files(source_f, 'female')
	print('\tMale...')
	df_male = load_files(source_m, 'male')

	print('Extracting DataPoints...')
	df_bothSex_DP = extract_datapoints(df_bothSex)
	df_female_DP = extract_datapoints(df_female)
	df_male_DP = extract_datapoints(df_male)


	#merge all the data together for all sexes
	df_all_MaleFemale = pd.concat([df_female_DP, df_male_DP], ignore_index = True)
	df_all_MaleFemale = df_all_MaleFemale.sort_values(by=['ref_area_code', 'year', 'gender', 'variant'])


	#produce files for both sex
	print('creating DataPoint files...')
	#first remove the both sex --gender column
	df_bothSex_DP = df_bothSex_DP.drop('gender', axis=1)

	#os.makedirs(os.path.dirname('ddf--datapoints--population--by--ref_area_code--year--variant'), exist_ok=True)

	for geo, idxs in df_bothSex_DP.groupby(by='ref_area_code').groups.items():
	    path = os.path.join(out_dir,'ddf--datapoints--population--by--ref_area_code--year--variant/ddf--datapoints--population--by--ref_area_code-{}--year--variant.csv'.format(geo))
	    to_save = df_bothSex_DP.ix[idxs]
	    to_save.ix[idxs].to_csv(path, index=False, float_format='%.15g')

	#produce files for Male and Female sex
	
	#os.makedirs(os.path.dirname('ddf--datapoints--population--by--ref_area_code--year--gender--variant'), exist_ok=True)
	
	for geo, idxs in df_all_MaleFemale.groupby(by='ref_area_code').groups.items():
	    path = os.path.join(out_dir,'ddf--datapoints--population--by--ref_area_code--year--gender--variant/ddf--datapoints--population--by--ref_area_code-{}--year--gender--variant.csv'.format(geo))
	    to_save = df_all_MaleFemale.ix[idxs]
	    to_save.ix[idxs].to_csv(path, index=False, float_format='%.15g')

	print('creating concepts files...')
	concepts = extract_concepts(df_bothSex[0])
	path = os.path.join(out_dir, 'ddf--concepts.csv')
	concepts.to_csv(path, index=False)
    

	print('creating entities files...')
	country = extract_entities_country(df_bothSex[0],df_bothSex[1],df_bothSex[2],df_bothSex[3])
	path = os.path.join(out_dir, 'ddf--entities--ref_area_code.csv')
	country.to_csv(path, index=False)

	gender = extract_entities_gender()
	path = os.path.join(out_dir, 'ddf--entities--gender.csv')
	gender.to_csv(path, index=False)

	variant = extract_entities_variant()
	path = os.path.join(out_dir, 'ddf--entities--variant.csv')
	variant.to_csv(path, index=False)

def main():
	generate_Population_Variance_Data()

	generate_Population_Age_Annual_Data()

	print('creating index files...')
	create_datapackage(out_dir)

if __name__ =='__main__':
    main()

	

	

