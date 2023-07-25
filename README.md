# Annual Technology Baseline Electricity Data Processing Pipeline

Python files and Jupyter notebooks for processing the Annual Technology Baseline (ATB) electricity data and determining LCOE and other metrics. All documentation and data for the ATB is available at the [ATB website](https://atb.nrel.gov).

## Installation and Requirements
The pipeline is known to work with [Python](https://www.python.org) 3.10.9 but other versions of Python will likely work. Dependancies can be installed with:

```
$ pip install -r requirements.txt
```

Once Python and all dependancies are installed, test that the installation is working correctly with:

```
$ pytest
```

The ATB pipeline uses [xlwings](https://www.xlwings.org/) for accessing the ATB data spreadsheet and requires a copy of Microsoft Excel. Currently the full pipeline will only run on MacOS and Windows. Linux support may be added in the future. 

**TODO** possibly include note about installing jupyter

## Running the ATB Electricity Pipeline
**TODO** - 

## Notable Directories
- `./lcoe_calculator` Extract technology metrics from the data master `xlsx` file and calculate LCOE using Python.
- `./debt_fraction_calculator` Given data and assumptions in the data master xlsx file, calculate debt fractions using PySAM.
- `./tests` Tests for code in this repository. 
