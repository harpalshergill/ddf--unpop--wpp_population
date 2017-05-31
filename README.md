# Population by age group from WPP

source: 

- UN Population WPP: https://esa.un.org/unpd/wpp/DVD/

- Includes Following Indicators:
BirthPer1000Population
ChildDependencyRatio
CrudeDeathRate
DependencyRatio
FeminityRatio
FertilityRate
InfantMortality
LifeExpectancy
MeanAgeForChildBearing
MedianAgeOfPopulation
Mortality
NetMigrationRate
NetNumberOfMigrants
NetReporductionRate
NoOfBirth
OldAgeDependencyRatio
PercentageTotalDeaths
PercentageTotalPopulation
Population
PopulationDensity
PopulationGrowthRate
PotentialSupport
RateOfNaturalIncrease
SexRatio
SurvivorAge
TotalDeaths
TotalFertility


## how to generate the dataset

1. download all of the source files above and put them into etl/source dir.
2. run in commandline: `cd etl/script && python pop_all.py`


## notes:

1. Etl folder contains two extra excel files: Metadata.xlsx and CountryMetadata.xlsx. 
Metadata.xlsx is a masterfile for all the indicators and naming for folders.
CountryMetadata.xlsx is masterfile for split of all the ref_area into World, Continent, Region and Country
2. Script supports multiple file loading and generate output into one file
3. Script also takes all Variants available in the excel file and generate variant dimention
4. NOTES sheet in each excel is not being included 
5. Population indicator and 14 other indicator have multiple files. Because of that the information in concept.csv file for "Name" and "Description" column is generic and hard coded. Information can be found at updateConceptDF function
6. File iterats trough all 95 files and generate ddf dataset in 15 mins or so. Hard disk space requirements is 1.5GB for new files
7. Because of size of files, validate-ddf can not be run on whole dataset. it's been tested on individual folders though to check the data integrity.
