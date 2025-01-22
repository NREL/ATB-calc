#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Version(s) of extractor class used by specific tech_processors when that
processor needs special functions beyond the basic Extractor
"""

from typing import List
import xlwings as xw

from .config import CrpChoiceType
from .extractor import Extractor


class PVBatteryExtractor(Extractor):
    """
    Extract financial assumptions, metrics, and WACC from Excel data workbook.
    For the PV-plus-battery technology, with unique tax credit cases
    """

    def __init__(
        self,
        data_workbook_fname: str,
        sheet_name: str,
        case: str,
        crp: CrpChoiceType,
        scenarios: List[str],
        base_year: int,
        tax_credit_case: str,
    ):
        """
        @param data_workbook_fname - file name of data workbook
        @param sheet_name - name of sheet to process
        @param case - 'Market' or 'R&D'
        @param crp - capital recovery period: 20, 30, or 'TechLife'
        @param scenarios - scenarios, e.g. 'Advanced', 'Moderate', etc.
        @param base_year - first year of data for this technology
        @param tax_credit_case - tax credit case: "PV PTC and Battery ITC" or "ITC only"
        """
        self._data_workbook_fname = data_workbook_fname
        self.sheet_name = sheet_name

        if tax_credit_case:
            # Open workbook, set tax credit case, and save
            wb = xw.Book(data_workbook_fname)
            sheet = wb.sheets[sheet_name]
            print("Setting tax credit case", tax_credit_case)
            sheet.range("Q46").value = tax_credit_case
            wb.save()

        super().__init__(
            data_workbook_fname, sheet_name, case, crp, scenarios, base_year
        )
