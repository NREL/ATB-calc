# Annual Technology Baseline Electricity Data Processing Pipeline

Python files and Jupyter notebooks for processing the Annual Technology Baseline (ATB) electricity data and determining LCOE and other metrics. All documentation and data for the ATB is available at the [ATB website](https://atb.nrel.gov).

## Installation and Requirements
The pipeline requires [Python](https://www.python.org) 3.10 or newer. Dependancies can be installed using `pip`: **TODO possibly include note about installing jupyter**


```
$ pip install -r requirements.txt
```

Once Python and all dependancies are installed, test that the installation is working with:

```
$ pytest
```

Tests take about a minute and should complete without errors. The ATB pipeline uses [xlwings](https://www.xlwings.org/) for accessing the ATB data spreadsheet and requires a copy of Microsoft Excel. Currently the full pipeline will only run on MacOS and Windows. Linux support may be added in the future. 

## Running the ATB Electricity Pipeline
Running the pipeline first requires downloaded the most current data in XLSX format from the [ATB website](https://atb.nrel.gov). The pipeline may be ran for one or all electricity technologies. Data may be exported in several formats. Below are several examples workflows. It is assumed all commands are run from the root directory of the repository. In the examples `{PATH-TO-DATA-MASTER}` is the relative or full path to the ATB electricity data master XLSX file.

Process all techs and export to a flat file named `flat_file.csv`:

```
$ python -m lcoe_calculator.full_scrape --save-flat flat_file.csv {PATH-TO-DATA-MASTER}
```

Process only land-based wind and export pivoted data and meta data:

```
$ python -m lcoe_calculator.full_scrape --tech LandBasedWindProc \
	--save-pivoted pivoted_file.csv --save-meta meta_file.csv {PATH-TO-DATA-MASTER}
```

Process only pumped storage hydropower and copy data to the clipboard so it may be pasted into a spreadsheet:

```
$ python -m lcoe_calculator.full_scrape --tech PumpedStorageHydroProc \
	--clipboard {PATH-TO-DATA-MASTER}
```

Help for the scraper and the names of available technologies can be viewed by running:

```
$ python -m lcoe_calculator.full_scrape --help
```



## Notable Directories
- `./lcoe_calculator` Extract technology metrics from the data master `xlsx` file and calculate LCOE using Python.
- `./debt_fraction_calculator` Given data and assumptions in the data master xlsx file, calculate debt fractions using PySAM.
- `./tests` Tests for code in this repository. 
