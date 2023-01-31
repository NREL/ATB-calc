import pandas as pd
import numpy as np
import xlwings as xw

BASE_YEAR = 2021
YEARS = list(range(BASE_YEAR, 2051 , 1))

FIN_CASES = ['Market', 'R&D']
FIN_ASSUMP_COL = 5  # Number of columns from fin assumption keys to values
TECH_DETAIL_SCENARIO_COL = 'tech_detail-scenario'  # Column name for combined
    # tech detail name and scenario, aka Column K in spreadsheet
NUM_WACC_PARMS = 24  # Number of rows of data for each tech in WACC Calc sheet


class Extractor:
    """
    Extract financial assumptions, metrics, and WACC from Excel datamaster.
    """
    wacc_sheet = 'WACC Calc'
    tax_credits_sheet = 'Tax Credits'

    def __init__(self, data_master_fname, sheet_name, case, crp, scenarios):
        """
        @param {str} data_master_fname - file name of data master
        @param {str} sheet_name - name of sheet to process
        @param {str} case - 'Market' or 'R&D'
        @param {int|str} crp - capital recovery period: 20, 30, or 'TechLife'
        @param {list} scenarios - scenarios, e.g. 'Advanced', 'Moderate', etc.
        """

        self._dm_fname = data_master_fname
        self.sheet_name = sheet_name
        assert case in FIN_CASES, f'Financial case "{case}" is not known'
        self._case = case
        self.scenarios = scenarios

        # Open spreadsheet, set fin case and CRP, and save
        wb = xw.Book(data_master_fname)
        sheet = wb.sheets['Financial and CRP Inputs']
        sheet.range('B5').value = case
        sheet.range('E5').value = crp
        wb.save()

        df = pd.read_excel(data_master_fname, sheet_name=sheet_name)
        df = df.reset_index()
        # Give columns numerical names
        columns = {x:y for x,y in zip(df.columns,range(0,len(df.columns)))}
        df = df.rename(columns=columns)
        self._df = df

        tables_start_row, _ = self._find_cell(df, 'Future Projections')
        tables_end_row, _ = self._find_cell(df, 'Data Sources for Default Inputs')
        self._df_tech_full = df.loc[tables_start_row:tables_end_row]
    
    @classmethod
    def get_tax_credits_sheet(cls, data_master_fname):
        """
        Pull tax credits from the Tax Credits sheet. It is assumed there is one empty row
        between ITC and PTC data. 

        @param {str} data_master_fname - file name of data master
        @returns {pd.DataFrame, pd.DataFrame} df_itc, df_ptc - data frames of 
            itc and ptc data.
        """
        df_tc = pd.read_excel(data_master_fname, sheet_name=cls.tax_credits_sheet)
        df_tc = df_tc.reset_index()

        # Give columns numerical names
        columns = {x:y for x,y in zip(df_tc.columns,range(0,len(df_tc.columns)))}
        df_tc = df_tc.rename(columns=columns)

        #First and last year locations in header
        fy_row, fy_col = cls._find_cell(df_tc, YEARS[0])
        ly_row, ly_col = cls._find_cell(df_tc, YEARS[-1])
        assert fy_row == ly_row, 'First and last year headings were not found on the same row '+\
            'on the tax credit sheet.'

        # Figure out location of data
        itc_row, itc_col = cls._find_cell(df_tc, 'ITC (%)')
        ptc_row, ptc_col = cls._find_cell(df_tc, 'PTC ($/MWh)')
        assert itc_col + 2 == fy_col, 'Expected first data column for ITC does not line up '+\
            'with first year heading.'
        assert ptc_col + 2 == fy_col, 'Expected first data column for PTC does not line up '+\
            'with first year heading.'
        assert itc_col == ptc_col, 'ITC and PTC marker text are not in the same column'
        
        # Pull years from tax credit sheet
        years = list(df_tc.loc[fy_row, fy_col:ly_col].astype(int).values)
        assert years == YEARS, 'Years in tax credit sheet ({years}) do not match ATB years ({YEARS})'

        # Pull ITC and PTC values
        df_itc = df_tc.loc[itc_row:ptc_row-2, itc_col+1:ly_col]
        df_itc.columns = ['Technology'] + years
        df_itc.index = df_itc.Technology
        df_itc.drop('Technology', axis=1, inplace=True)

        df_ptc = df_tc.loc[ptc_row:, ptc_col+1:ly_col]
        df_ptc.columns = ['Technology'] + years
        df_ptc.index = df_ptc.Technology
        df_ptc.drop('Technology', axis=1, inplace=True)
        df_ptc = df_ptc.dropna()

        return df_itc, df_ptc

    def get_wacc(self, tech_name=None):
        """
        Extract values for tech and case from WACC sheet.

        @param {str|None} tech_name - name of tech to search for on WACC sheet.
            Use sheet name if None

        @returns {pd.DataFrame} df_wacc - all WACC values
        @returns {pd.DataFrame} df_just_wacc - last six rows of wacc sheet,
            'WACC Nominal - {scenario}' and 'WACC Real - {scenario}'
        """
        df_wacc = pd.read_excel(self._dm_fname, self.wacc_sheet)
        case = 'Market Factors' if self._case == 'Market' else 'R&D'
        tech_name = self.sheet_name if tech_name is None else tech_name
        search = f'{tech_name} {case}'

        count = (df_wacc == search).sum().sum()
        if count != 1:
            assert count != 0, f'Unable to find "{search}" on {self.wacc_sheet} sheet.'
            assert count <= 1, f'"{search}" found more than once in {self.wacc_sheet} sheet.'

        start_row, c = self._find_cell(df_wacc, search)
        assert c == 'Unnamed: 0', f'WACC Calc tech search string ("{search}") found in wrong column'

        # Grab the rows, reset index and columns
        df_wacc = df_wacc.iloc[start_row:start_row + NUM_WACC_PARMS + 1]
        df_wacc = df_wacc.set_index('Unnamed: 1')
        df_wacc.columns = df_wacc.iloc[0]

        # Drop empty columns and first row w/ years
        df_wacc = df_wacc.dropna(axis=1, how='any').drop(df_wacc.index[0])
        df_wacc.index.rename('WACC', inplace=True)
        df_wacc.columns.name = 'year'

        df_just_wacc = df_wacc.iloc[-6:]
        df_just_wacc.index.rename('WACC Type', inplace=True)

        idx = df_wacc.index
        assert idx[0] == 'Inflation Rate' and idx[-1] == 'WACC Real - Conservative', \
            ('"Inflation Rate" should be the first row in the WACC table and '
             f'"WACC Real - Conservative" should be last, but "{idx[0]}" and '
             f'"{idx[-1]}" were found instead. Please check the data master '
             f'spreadsheet and NUM_WACC_PARAMS.')

        cols = df_wacc.columns
        assert cols[0] == YEARS[0], f'WACC: First year should be {YEARS[0]}, got {cols[0]} instead'
        assert cols[-1] == YEARS[-1], f'WACC: Last year should be {YEARS[-1]}, got {cols[-1]} instead'

        return df_wacc, df_just_wacc

    def get_fin_assump(self):
        """
        Dynamically search for financial assumptions in small table at top of
        tech sheet and return as dataframe

        @returns {pd.DataFrame}
        """
        r1, c = self._find_cell(self._df, 'Financial Assumptions:')
        r2 = r1 + 1
        val = self._df.loc[r2, c]
        while not (self._is_empty(val) or val == 'Construction Duration yrs'):
            r2 += 1
            assert r2 != self._df.shape[0], "Error finding end of fin assumptions"
            val = self._df.loc[r2, c]

        headers = ['Financial Assumptions', 'Value']

        df_fin_assump = pd.DataFrame(self._df.loc[r1 + 1:r2, c])
        df_fin_assump['Value'] = self._df.loc[r1 + 1:r2, c + FIN_ASSUMP_COL]
        df_fin_assump.columns = headers
        df_fin_assump = df_fin_assump.set_index('Financial Assumptions')
        return df_fin_assump

    def get_metric_values(self, metric, num_tds, split_metrics=False):
        """
        Grab metric values table

        @param {str} metric - name of desired metric
        @param {int} num_tds - number of tech resource groups
        @param {bool} split_metrics - metric has blanks in between tech details if True
        @returns {pd.DataFrame}
        """

        num_rows = len(self.scenarios) * num_tds
        if split_metrics:
            num_rows += len(self.scenarios)

        df_met = self._get_metric_values(metric, num_rows)

        assert len(df_met) == num_tds * len(self.scenarios), \
            (f'{metric} of {self.sheet_name} '
            f'appears to be corrupt or the wrong number of tech details ({num_tds}) '
            f'was entered. split_metrics = {split_metrics}.')

        return df_met

    def get_tax_credits(self):
        # HACK - 30 is arbitrary, but works
        df_tc = self._get_metric_values('Tax Credit', 30)
        df_tc.index.name = 'Tax Credit'
        return df_tc

    def get_cff(self, cff_name, rows):
        """
        Pull CFF values

        @param {str} cff_name - name of CFF data in SS
        @param {int} rows - number of CFF rows to pull
        @returns {pd.DataFrame} - CFF dataframe
        """
        df_cff = self._get_metric_values(cff_name, rows)
        df_cff.index.name = cff_name
        return df_cff

    def _get_metric_values(self, metric, num_rows):
        """
        Grab metric values table

        @param {str} metric - name of desired metric
        @param {int} num_rows - number of rows to pull
        @returns {pd.DataFrame}
        """
        # Determine bounds of data
        r, c = self._find_cell(self._df_tech_full, metric)
        first_row = r
        end_row = r + num_rows - 1
        first_col = c + 1
        end_col = self._next_empty_col(self._df_tech_full, r, first_col) - 1

        # Extract headings
        year_headings = self._df_tech_full.loc[first_row - 1, first_col + 2:end_col]
        year_headings = list(year_headings.astype(int))

        # Extract data
        df_met = self._df_tech_full.loc[first_row:end_row, first_col:end_col]

        assert first_col < end_col,\
            (f'There is a formatting error for {metric} in {self.sheet_name}. '
             f'Extracted:\n{str(df_met)}')

        # Create index from tech details and cases
        df_met[first_col] = df_met[first_col].astype(str) + '/' +\
             df_met[first_col + 1].astype(str)
        df_met = df_met.set_index(first_col).drop(first_col + 1, axis=1)

        # Clean up
        df_met.columns = year_headings
        df_met.index.name = TECH_DETAIL_SCENARIO_COL
        df_met = df_met.dropna(how='all')

        cols = df_met.columns
        assert cols[0] == YEARS[0], f'{metric}: First year should be {YEARS[0]}, got {cols[0]} instead'
        assert cols[-1] == YEARS[-1], f'{metric}: Last year should be {YEARS[-1]}, got {cols[-1]} instead'

        return df_met

    @staticmethod
    def _is_empty(val):
        if isinstance(val, str):
            return False
        if val == '':
            return True
        if np.isnan(val):
            return True
        return False

    @staticmethod
    def _find_cell(df, value):
        """
        Search dataframe for one instance of a value.

        @param {str} value - value to search for
        @returns {str|int, str|int} index, column - index and column of value in
            dataframe
        """
        count = (df == value).sum().sum()
        if count != 1:
            assert count != 0, f'Dataframe has no instances of "{value}"'
            assert count <= 1, f'Dataframe has more than one instance of "{value}"'

        cell = df.where(df==value).dropna(how='all').dropna(axis=1)
        return cell.index[0], cell.columns[0]

    def _next_empty_col(self, df, row, col1):
        """
        Find next empty column in a row, starting at col1, or the end of
        the row.
        """
        col2 = col1 + 1
        while not self._is_empty(df.loc[row, col2]):
            col2 += 1
            if col2 == len(df.loc[row]):
                return col2
        return col2