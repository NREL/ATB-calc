# ATB Calculator
This code scrapes the ATB data master Excel spreadsheet, calculates LCOE and CAPEX
for all technologies as needed, and exports data in flat or flat + pivoted formats.

**Note:** You will likely have to give Python access to interact with Excel. A window will automatically ask for permission the first time this script is run.

## Files
Files are listed in roughly descending order of importance and approachability.

 - `full_scrape.py` - Class that performs full scrape with built in command line interface. See the README in the root of this repo for CLI examples.
 - `tech_processors.py` - Classes to scrape and process individual technologies. Any new ATB technologies should be added to this file.
 - `base_processor.py` - Base processor class that is subclassed to process individual technologies.
 - `extractor.py` - Code to pull values from the spreadsheet
 - `macrs.py` - MACRS depreciation schedules

## Jupyter Notebooks
Notebooks demonstrating how to use the the code in this directory.

 - `Full work flow.ipynb` - Jupter notebook for testing full scrape.
 - `Test Tech processors.ipynb` - Jupyter notebook for testing individual techs. May not be up-to-date.
 - `Test Tax Credit Scrape.ipynb` - Jupyter notebook for testing and demonstrating the tax credit scraper.


