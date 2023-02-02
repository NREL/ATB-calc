# ATB Electricity Data Processing Pipeline

Python files and Jupyter notebooks for processing ATB electricity data and determining LCOE and other metrics. There are several generations of files in this repo.

## Notable Files and Directories
- `./lcoe_calculator` Extract technology metrics from the data master xlsx file and calculate LCOE using Python
- `./debt_fraction_calculator` Given data and assumptions in the data master xlsx file, calculate debt fractions using PySAM
- `./drop_down_scraping` Legacy scraper for 2022 data master. Has not been tested with 2023, but should work
- `./vba_scraping` Legacy scrapers for data masters from 2021 and earlier
- **TODO**: Describe all the other files
