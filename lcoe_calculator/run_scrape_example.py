"""
Example full scrape work flow.
"""
from datetime import datetime as dt
from full_scrape import FullScrape

# Data master version on sharepoint - empty string if you haven't renamed the file
version_string = "_v5.1"

# Path to data master spreadsheet
data_master_filename = '../2023-ATB-Data_Master' + version_string + '.xlsx'


# Kick off scraper
scraper = FullScrape(data_master_filename)
start = dt.now()
scraper.scrape()
print('Scrape complete in ', dt.now()-start)

# The pivot data has each year as its own column
print('Pivoted data:')
print(scraper.data)

# In the flat data, each year gets it's own row. Years are in the 'variable'
# column, the parameter value is in the 'value' column
print('Flat data:')
print(scraper.data_flattened)

# Save pivot data to CSV
if False:
    scraper.to_csv('pivoted' + version_string + '.csv')

# Save flattened data to CSV
if True:
    scraper.flat_to_csv('flat' + version_string + '.csv')

# Save meta data to CSV
if True:
    scraper.meta_data_to_csv('meta' + version_string + '.csv')

# Copy data to clipboard to paste into excel
if False:
    scraper.data.to_clipboard()
