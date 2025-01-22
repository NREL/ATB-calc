#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Mock data extractor for testing.
"""
from typing import List, Optional, Tuple
import pandas as pd
from lcoe_calculator.abstract_extractor import AbstractExtractor
from lcoe_calculator.config import CrpChoiceType
from .data_finder import (
    DataFinder,
    TAX_CREDIT_FAKE_SS_NAME,
    WACC_FAKE_SS_NAME,
    JUST_WACC_FAKE_SS_NAME,
    FIN_ASSUMP_FAKE_SS_NAME,
)


class MockExtractor(AbstractExtractor):
    """
    Mock data extractor for testing. Loads all data from ./data directory instead of from data
    workbook.

    The DataFinder class must be initialized with DataFinder.set_tech() and the TechProcessor class
    before MockExtractor is used to to load data from the data directory.
    """

    def __init__(
        self,
        _: str,
        __: str,
        case: str,
        crp: CrpChoiceType,
        ___: List[int],
        ____: int,
        _____: Optional[str] = None,
    ):
        """
        @param data_workbook_fname - IGNORED
        @param sheet_name - IGNORED
        @param case - 'Market' or 'R&D'
        @param crp - capital recovery period: 20, 30, or 'TechLife'
        @param scenarios - IGNORED
        @param base_year - IGNORED
        @param tax_credit_case - IGNORED, only used by PV+Battery
        """
        self._case = case
        self._requested_crp = crp

    def get_metric_values(self, metric: str, _: int, __=False) -> pd.DataFrame:
        """
        Grab metric values table

        @param metric - long name of desired metric
        @param num_tds - IGNORED
        @param split_metrics - IGNORED
        @returns
        """
        fname = DataFinder.get_data_filename(metric, self._case, self._requested_crp)
        df = self.read_csv(fname)
        return df

    def get_tax_credits(self) -> pd.DataFrame:
        """Get tax credit"""
        fname = DataFinder.get_data_filename(
            TAX_CREDIT_FAKE_SS_NAME, self._case, self._requested_crp
        )
        df = self.read_csv(fname)
        return df

    def get_cff(self, cff_name: str, _) -> pd.DataFrame:
        """
        Pull CFF values

        @param {str} cff_name - name of CFF data in SS
        @param {int} rows - number of CFF rows to pull
        @returns {pd.DataFrame} - CFF dataframe
        """
        fname = DataFinder.get_data_filename(cff_name, self._case, self._requested_crp)
        df = self.read_csv(fname)
        return df

    def get_fin_assump(self) -> pd.DataFrame:
        """
        Dynamically search for financial assumptions in small table at top of
        tech sheet and return as data frame
        """
        fname = DataFinder.get_data_filename(
            FIN_ASSUMP_FAKE_SS_NAME, self._case, self._requested_crp
        )
        df = pd.read_csv(fname, index_col=0)
        return df

    def get_wacc(self, _=None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract values for tech and case from WACC sheet.

        @param IGNORED
        @returns {pd.DataFrame} df_wacc - all WACC values
        @returns {pd.DataFrame} df_just_wacc - last six rows of wacc sheet,
            'WACC Nominal - {scenario}' and 'WACC Real - {scenario}'
        """
        fname = DataFinder.get_data_filename(
            WACC_FAKE_SS_NAME, self._case, self._requested_crp
        )
        df_wacc = self.read_csv(fname)
        fname = DataFinder.get_data_filename(
            JUST_WACC_FAKE_SS_NAME, self._case, self._requested_crp
        )
        df_just_wacc = self.read_csv(fname)
        return (df_wacc, df_just_wacc)

    @staticmethod
    def read_csv(fname: str) -> pd.DataFrame:
        """
        Read a CSV and convert columns to ints

        @param fname - file to read
        @returns data in the CSV
        """
        df = pd.read_csv(fname, index_col=0)
        df.columns = df.columns.astype(int)
        return df
