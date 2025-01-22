#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
from typing import List, Tuple
from abc import ABC, abstractmethod
import pandas as pd

from .config import CrpChoiceType


class AbstractExtractor(ABC):
    """
    Minimal interface required for a data extractor class
    """

    @abstractmethod
    def __init__(
        self,
        data_workbook_fname: str,
        sheet_name: str,
        case: str,
        crp: CrpChoiceType,
        scenarios: List[str],
        base_year: int,
    ):
        """
        @param data_workbook_fname - file name of data workbook
        @param sheet_name - name of sheet to process
        @param case - 'Market' or 'R&D'
        @param crp - capital recovery period: 20, 30, or 'TechLife'
        @param scenarios - scenarios, e.g. 'Advanced', 'Moderate', etc.
        @param base_year - first year of data for this technology
        """

    @abstractmethod
    def get_metric_values(
        self, metric: str, num_tds: int, split_metrics: bool = False
    ) -> pd.DataFrame:
        """
        Grab metric values table.

        @param metric - name of desired metric
        @param num_tds - number of tech resource groups
        @param split_metrics - metric has blanks in between tech details if True
        @returns data frame for metric
        """

    @abstractmethod
    def get_tax_credits(self) -> pd.DataFrame:
        """Get tax credit"""

    @abstractmethod
    def get_cff(self, cff_name: str, rows: int) -> pd.DataFrame:
        """
        Pull CFF values

        @param cff_name - name of CFF data in SS
        @param rows - number of CFF rows to pull
        @returns CFF data frame
        """

    @abstractmethod
    def get_fin_assump(self) -> pd.DataFrame:
        """
        Dynamically search for financial assumptions in small table at top of tech sheet and return
        as data frame.

        @returns financial assumption data
        """

    @abstractmethod
    def get_wacc(
        self, tech_name: str | None = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract values for tech and case from WACC sheet.

        @param tech_name - name of tech to search for on WACC sheet. Use sheet name if None.

        @returns df_wacc - all WACC values
        @returns df_just_wacc - last six rows of wacc sheet, 'WACC Nominal - {scenario}' and 'WACC
                                Real - {scenario}'
        """
