# ATB Calculator
This code scrapes the Excel ATB data workbook, then calculates LCOE and CAPEX for all technologies
as needed, and exports data in flat or flat + pivoted formats.

**Note:** You will likely have to give Python access to interact with Excel. A window will
automatically ask for permission the first time this script is run.

## Files
Files are listed in roughly descending order of importance and approachability.

 - `full_scrape.py` - Class that performs full scrape with built in command line interface. See the README in the root of this repo for CLI examples.
 - `tech_processors.py` - Classes to process individual technologies. Any new ATB technologies should be added to this file.
 - `base_processor.py` - Base processor class that is subclassed to process individual technologies.
 - `config.py` - Constant definitions including the base year and scenario names
 - `extractor.py` - Code to pull values from the workbook
 - `abstract_extractor.py` - Abstract version of abstractor to allow for mock values in tests
 - `macrs.py` - MACRS depreciation schedules



