#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also
# https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Config and constants for the LCOE pipeline.
"""
from enum import Enum
from typing import Literal, List

BASE_YEAR = 2023
END_YEAR = 2060

YEARS = list(range(BASE_YEAR, END_YEAR + 1, 1))
""" Years of data projected by ATB """


class FinancialCases(Enum):
    """
    Enum for financial cases.
    """

    MARKET_COST = "Market Cost"
    """ Market financials and cost case"""

    MARKET = "Market"
    """ Market financials only"""

    R_AND_D = "R&D"
    """ Research and Development financials only"""


# Tax credit cases
ITC_ONLY_CASE = "ITC only"
PTC_PLUS_ITC_CASE_PVB = "PV PTC and Battery ITC"
TAX_CREDIT_CASES = {"Utility-Scale PV-Plus-Battery": [ITC_ONLY_CASE, PTC_PLUS_ITC_CASE_PVB]}

# CRP choices and type hints
CrpChoiceType = Literal[20, 30, "TechLife"]
CRP_CHOICES: List[CrpChoiceType] = [20, 30, "TechLife"]

# Technology advancement scenarios
SCENARIOS = ["Advanced", "Moderate", "Conservative"]

# Column name for combined tech detail name and scenario, aka Column K in the workbook
TECH_DETAIL_SCENARIO_COL = "tech_detail-scenario"

# Metric header names in ATB data workbook (usually column J)
LCOE_CELL_NAME = "Levelized Cost of Energy ($/MWh)"
CAPEX_CELL_NAME = "CAPEX ($/kW)"
CFF_CELL_NAME = "Construction Finance Factor"
REFERENCES_CELL_NAME = "References"
