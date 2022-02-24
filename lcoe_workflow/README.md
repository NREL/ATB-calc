# ATB Data Scraper
This code scrapes the ATB data master Excel spreadsheet, calculates LCOE and CAPEX
for all technologies as needed, and exports data in flat or flat + pivoted formats.

## Files
Files are listed in roughly descending order of importance and approachability.

 - `run_scrape_example.py` - Example file for running a full scrape, calculating LCOE and CAPEX, and exporting data to a CSV. If you don't know what you're doing, look at this file.
 - `full_scrape.py` - Class that performs full scrape.
 - `tech_processors.py` - Classes to scrape and process individual technologies. Any new ATB technologies should be added to this file.
 - `base_processor.py` - Base processor class that is subclassed to process individual technologies.
 - `extractor.py` - Code to pull values from the spreadsheet
 - `macrs.py` - MACRS depreciation schedules
 - `Test Tech processors.ipynb` - Jupyter notebook for testing individual techs. May not be up-to-date.
 - `Full work flow.ipynb` - Jupter notebook for testing full scrape. May not be up-to-date.

## Dependencies
The scraper is known to work with Python 3.8.12. The following packages are required.

 - numpy
 - pandas
 - xlwings - OS agnostic Excel automator