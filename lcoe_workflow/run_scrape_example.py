"""
Example fullscrape work flow.
"""
from datetime import datetime as dt
from full_scrape import FullScrape

# Path to data master spreadsheet
data_master_filename = '../../datamaster_working/2022-ATB-Data_Master.xlsx'

# Kick off scraper
scraper = FullScrape(data_master_filename)
start = dt.now()
scraper.scrape()
print('Scrape complete in ', dt.now()-start)

# The flat data has each year as its own column
print('Flat data:')
print(scraper.data)

# In the pivoted data, each year gets it's own row. Years are in the 'variable'
# column, the parameter value is in the 'value' column
print('Flat data pivoted:')
print(scraper.data_pivoted)

# Save flat data to CSV
if False:
    scraper.to_csv('flat.csv')

# Save pivoted data to CSV
if False:
    scraper.pivoted_to_csv('pivoted.csv')

# Copy data to clipboard to paste into excel
if False:
    scraper.data.to_clipboard()