"""
Config and constants for the LCOE pipeline.
"""
from typing import Literal

# Years of data predicted by ATB
BASE_YEAR = 2021
YEARS = list(range(BASE_YEAR, 2051 , 1))

# Financial cases
MARKET_FIN_CASE = 'Market'
R_AND_D_FIN_CASE = 'R&D'
FINANCIAL_CASES = [MARKET_FIN_CASE, R_AND_D_FIN_CASE]

# CRP choices and type hints
CRP_CHOICES = [20, 30, 'TechLife']
CrpChoiceType = Literal[20, 30, 'TechLife']

# Technology advancement scenarios
SCENARIOS = ['Advanced', 'Moderate', 'Conservative']

# Column name for combined tech detail name and scenario, aka Column K in spreadsheet
TECH_DETAIL_SCENARIO_COL = 'tech_detail-scenario'

# Metric header names in data master spreadsheet
LCOE_SS_NAME = 'Levelized Cost of Energy ($/MWh)'
CAPEX_SS_NAME = 'CAPEX ($/kW)'
CFF_SS_NAME = 'Construction Finance Factor'