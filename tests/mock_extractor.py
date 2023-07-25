"""
Mock data extractor for testing.
"""
from typing import List, Tuple
import pandas as pd
from lcoe_calculator.extractor import AbstractExtractor
from .data_finder import DataFinder, TAX_CREDIT, WACC, JUST_WACC, FINANCIAL_ASSUMPTIONS

class MockExtractor(AbstractExtractor):
    """
    Mock data extractor for testing. Loads all data from ./data directory instead of from data
    master spreadsheet.

    The DataFinder class must be initialized with DataFinder.set_tech() and the TechProcessor class
    before MockExtractor is used to to load data from the data directory.
    """

    def __init__(self, _: str, __: str, case: str, crp: str | int, ___: List[int],
                 ____: int | None = None):
        """
        @param data_master_fname - IGNORED
        @param sheet_name - IGNORED
        @param case - 'Market' or 'R&D'
        @param crp - capital recovery period: 20, 30, or 'TechLife'
        @param scenarios - IGNORED
        @param base_year - IGNORED
        """
        self._case = case
        self._crp = crp

    def get_metric_values(self, metric: str, _:int, __=False) -> pd.DataFrame:
        """
        Grab metric values table

        @param metric - long name of desired metric
        @param num_tds - IGNORED
        @param split_metrics - IGNORED
        @returns
        """
        fname = DataFinder.get_data_filename(metric, self._case, self._crp)
        df = self.read_csv(fname)
        return df

    def get_tax_credits(self) -> pd.DataFrame:
        """ Get tax credit """
        fname = DataFinder.get_data_filename(TAX_CREDIT, self._case, self._crp)
        df = self.read_csv(fname)
        return df

    def get_cff(self, cff_name: str, _) -> pd.DataFrame:
        """
        Pull CFF values

        @param {str} cff_name - name of CFF data in SS
        @param {int} rows - number of CFF rows to pull
        @returns {pd.DataFrame} - CFF dataframe
        """
        fname = DataFinder.get_data_filename(cff_name, self._case, self._crp)
        df = self.read_csv(fname)
        return df

    def get_fin_assump(self) -> pd.DataFrame:
        """
        Dynamically search for financial assumptions in small table at top of
        tech sheet and return as data frame
        """
        fname = DataFinder.get_data_filename(FINANCIAL_ASSUMPTIONS, self._case, self._crp)
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
        fname = DataFinder.get_data_filename(WACC, self._case, self._crp)
        df_wacc = self.read_csv(fname)
        fname = DataFinder.get_data_filename(JUST_WACC, self._case, self._crp)
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
