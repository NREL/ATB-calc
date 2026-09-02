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
    Possible financial cases for ATB technologies. All techs support the R&D financial cases, but
    not all techs support the expanded financial cases.
    """

    EXPANDED_WITHOUT_TAX_CREDITS = "Exp"
    """ Expanded Cost Drivers without tax credits"""

    EXPANDED_WITH_TAX_CREDITS = "Exp + TC"
    """ Expanded Cost Drivers withtax credits"""

    R_AND_D_WITHOUT_TAX_CREDITS = "R&D"
    """ R&D Cost Drivers Without Tax Credits"""

    R_AND_D_WITH_TAX_CREDITS = "R&D + TC"
    """ R&D Cost Drivers With Tax Credits"""


EXPANDED_FINANCIAL_CASES = [
    FinancialCases.EXPANDED_WITHOUT_TAX_CREDITS,
    FinancialCases.EXPANDED_WITH_TAX_CREDITS,
]
""" Both expanded financial cases"""

WITHOUT_TAX_CREDITS_CASES = [
    FinancialCases.EXPANDED_WITHOUT_TAX_CREDITS,
    FinancialCases.R_AND_D_WITHOUT_TAX_CREDITS,
]
""" Both financial cases without tax credits"""

WITH_TAX_CREDITS_CASES = [
    FinancialCases.EXPANDED_WITH_TAX_CREDITS,
    FinancialCases.R_AND_D_WITH_TAX_CREDITS,
]
""" Both financial cases without tax credits"""

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
