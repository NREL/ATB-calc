import pandas as pd
import numpy as np

from extractor import Extractor, FIN_CASES, YEARS, TECH_DETAIL_SCENARIO_COL

CRP_CHOICES = ['20', '30', 'TechLife']
TOL = 1e-6  # Tolerance for comparing if a float is zero


class TechProcessor:
    """
    Base abstract tech-processor class. This must be sub-classed to be used. See
    tech_processors.py Various class vars like sheet_name must be over-written
    by sub-classes, things like tech_life can be as needed.  Functions for
    _capex(), _con_fin_cost(), etc can be over-written as needed, e.g.
    Geothermal.

    Notable methods:

    __init__() - Constructor. Various class attribute sanity checks and loads
                 data from spreadsheet.
    run() - Perform all calcs to determine CAPEX and LCOE.
    flat - (property) Convert fin assumptions and values in flat_attrs to a flat
           DataFrame
    test_lcoe() - Compare calculated LCOE to LCOE in spreadsheet.
    test_capex() - Compare calculated CAPEX to CAPEX in spreadsheet.
    """

    # ----------- These attributes must be set for each tech --------------
    sheet_name = None  # Name of the sheet in the excel data master
    tech_name = None  # Name of tech for flat file
    depreciation_schedule = None  # MACRS_6, etc.

    # ------------ All other attributes have defaults -------------------------
    # Metrics to load from SS. Format: (header in SS, object attribute name)
    metrics = [
        ('Net Capacity Factor (%)', 'df_ncf'),
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    tech_life = 30  # Tech lifespan in years
    num_tds = 10  # Number of technical resource groups
    scenarios = ['Advanced', 'Moderate', 'Conservative']

    has_ptc = True  # Does the tech quality for a Production Tax Credit?
    has_itc = True  # Does the tech qualify for an Investment Tax Credit?
    has_tax_credit = True  # Does the tech have tax credits in spread sheet
    has_fin_assump = True  # Does the tech have financial assumptions in spread sheet

    split_metrics = False  # Indicates 3 empty rows in tech detail metrics, e.g. hydropower

    wacc_name = None  # Name of tech to look for on WACC sheet, use sheet name if None
    has_lcoe_and_wacc = True  # If True, pull values from WACC sheet and calculate CRF,
                              # PFF, & LCOE. Techs that have WACC but not LCOE will need
                              # to overload run() (e.g., pumped storage hydro)

    # Attributes to export in flat file, format: (attr name in class, value for
    # flat file). Any attributes that are None are silently ignored. Financial
    # assumptions values are added automatically.
    flat_attrs = [
        ('df_ncf', 'CF'),
        ('df_occ', 'OCC'),
        ('df_gcc', 'GCC'),
        ('df_fom', 'Fixed O&M'),
        ('df_vom', 'Variable O&M'),
        ('df_cfc', 'CFC'),
        ('df_lcoe', 'LCOE'),
        ('df_capex', 'CAPEX'),
    ]

    def __init__(self, data_master_fname, case='Market', crp=30):
        """
        @param {str} data_master_fname - name of spreadsheet
        @param {str} case - financial case to run: 'Market' or 'R&D'
        @param {int|str} crp - capital recovery period: 20, 30, or 'TechLife'
        """
        assert case in FIN_CASES, (f'Financial case must be one of {FIN_CASES},'
            f' received {case}')
        assert str(crp) in CRP_CHOICES, (f'Financial case must be one of {CRP_CHOICES},'
            f' received {crp}')
        assert isinstance(self.scenarios, list), 'self.scenarios must be a list'

        for attr in ['sheet_name', 'tech_name', 'depreciation_schedule']:
            assert getattr(self, attr) is not None, \
                f'{attr} must be defined in tech sub-classes. Currently is None.'

        self._data_master_fname = data_master_fname
        self._case = case
        self._crp = crp  # 20, 30, or 'TechLife'
        self._crp_years = self.tech_life if crp == 'TechLife' else int(crp)

        # These data frames are extracted from excel
        self.df_ncf = None  # Net capacity factor (%)
        self.df_occ = None  # Overnight capital cost ($/kW)
        self.df_gcc = None  # Grid connection costs ($/kW)
        self.df_fom = None  # Fixed O&M ($/kW-yr)
        self.df_vom = None  # Variable O&M ($/MWh)
        self.df_tc = None  # Tax credits (varies)
        self.df_wacc = None  # WACC table (varies)
        self.df_just_wacc = None  # Last six rows of WACC table

        # These data frames are calculated and populated by object methods
        self.df_aep = None  # Annual energy production (kWh/kW)
        self.df_capex = None  # CAPEX ($/kW)
        self.df_cfc = None  # Construction finance cost ($/kW)
        self.df_crf = None  # Capital recovery factor - real (%)
        self.df_pff = None  # Project finance factor (unitless)
        self.df_lcoe = None  # LCOE ($/MWh)

        self._extractor = self._extract_data()

    def run(self):
        """ Run all calculations for CAPEX and LCOE"""
        self.df_aep = self._calc_aep()
        self.df_capex = self._calc_capex()
        self.df_cfc = self._calc_con_fin_cost()

        if self.has_lcoe_and_wacc:
            self.df_crf = self._calc_crf()
            self.df_pff = self._calc_pff()
            self.df_lcoe = self._calc_lcoe()

    @property
    def flat(self):
        """
        Return flattened data, joining all outputs. Split tech detail and
        scenario into separate columns and append tech, parameter name, case and
        crp. Include financial if present. Outputs are defined in self.flat_attrs,
        but are silently skipped if value attribute value is None.

        @returns {pd.DataFrame} - flat data for tech
        """
        df_flat = pd.DataFrame() if self.df_wacc is None else self._flat_fin_assump()

        case = self._case.upper()
        if case == 'MARKET':
            case = 'Market'

        for attr, parameter in self.flat_attrs:
            df = getattr(self, attr)
            if df is None:
                continue
            df = df.reset_index()

            old_cols = df.columns
            df[['DisplayName', 'Scenario']] = df[TECH_DETAIL_SCENARIO_COL].str\
                .rsplit('/', 1, expand=True)
            df.DisplayName = df.DisplayName.str.strip()
            df.Scenario = df.Scenario.str.strip()
            df['Parameter'] = parameter
            df_flat = pd.concat([df_flat, df])

        df_flat['Technology'] = self.tech_name
        df_flat['Case'] = case
        df_flat['CRPYears'] = self._crp_years

        new_cols = ['Parameter', 'Case', 'CRPYears', 'Technology', 'DisplayName',
                    'Scenario'] + list(old_cols)
        df_flat = df_flat[new_cols]
        df_flat = df_flat.drop(TECH_DETAIL_SCENARIO_COL, axis=1).reset_index(drop=True)

        return df_flat

    def test_lcoe(self):
        """
        Test calculated LCOE against values in spreadsheet. Raise exception
        if there is a discrepancy.
        """
        if not self.has_lcoe_and_wacc:
            print(f'LCOE is not calculated for {self.sheet_name}.')
            return
        assert self.df_lcoe is not None, 'Please run `run()` first to calculate LCOE.'

        self.ss_lcoe = self._extractor.get_metric_values('Levelized Cost of Energy ($/MWh)',
                                                 self.num_tds, self.split_metrics)

        if abs(self.ss_lcoe.subtract(self.df_lcoe).sum().sum()) < TOL:
            print('Calculated LCOE matches LCOE from spreadsheet')
        else:
            print("Spreadsheet LCOE")
            print(self.ss_lcoe)
            print("DF LCOE:")
            print(self.df_lcoe)
            raise ValueError('Calculated LCOE doesn\'t match LCOE from spreadsheet')

    def test_capex(self):
        """
        Test calculated CAPEX against values in spreadsheet. Raise exception
        if there is a discrepancy.
        """
        assert self.df_capex is not None, 'Please run `run()` first to calculate CAPEX.'
        self.ss_capex = self._extractor.get_metric_values('CAPEX ($/kW)', self.num_tds,
                                                     self.split_metrics)

        if abs(self.ss_capex.subtract(self.df_capex).sum().sum()) < TOL:
            print('Calculated CAPEX matches CAPEX from spreadsheet')
        else:
            raise ValueError('Calculated CAPEX doesn\'t match CAPEX from spreadsheet')

    def _flat_fin_assump(self):
        """
        Financial assumptions from WACC_Calc sheet by year for flat output: add
        FCR and reformat index.

        @returns {pd.DataFrame}
        """
        assert self.df_wacc is not None, ('df_wacc must not be None to flatten '
            'financial assumptions.')

        df = self.df_wacc.copy()

        # Add CRF and FCR
        if self.has_tax_credit and self.df_pff is not None:
            for scenario in self.scenarios:
                wacc = df.loc[f'WACC Real - {scenario}']
                pff = self.df_pff.loc[f'PFF - {scenario}']
                crf, fcr = self._calc_fcr(wacc, self._crp_years, pff, scenario)
                df = df.append([crf, fcr])
        else:
            # No tax credit, just fill with *
            cols = df.columns
            fcr = pd.DataFrame({c:['*'] for c in cols}, index=['FCR'])
            crf = pd.DataFrame({c:['*'] for c in cols}, index=['CRF'])
            df = df.append([crf, fcr])

        # Explode index and clean up
        df.index.rename('WACC', inplace=True)
        df = df.reset_index(drop=False)
        df[['Parameter', 'Scenario']] = df.WACC.str.split(' - ', expand=True)
        df.loc[df.Scenario.isnull(), 'Scenario'] = '*'
        df.loc[df.Scenario == 'Nominal', 'Parameter'] = 'Interest During Construction - Nominal'
        df.loc[df.Scenario == 'Nominal', 'Scenario'] = '*'
        df['DisplayName'] = '*'

        return df

    @staticmethod
    def _calc_fcr(wacc, crp, pff, scenario):
        """
        Calculate CRF and FCR for all years

        @param {pd.Series} wacc - WACC by year
        @param {int} crp - CRP
        @param {pd.Series} pff - project finance factor by year
        @param {str} scenario - name of financial scenario

        @returns {pd.DataFrame, pd.DataFrame} - CRF and FCR
        """
        crf = wacc/(1 - 1/(1 + wacc)**crp)
        fcr = crf*pff
        crf.name = f'CRC - {scenario}'
        fcr.name = f'FCR - {scenario}'
        crf = pd.DataFrame(crf).T
        fcr = pd.DataFrame(fcr).T

        return crf, fcr

    def _extract_data(self):
        """ Pull all data from spread sheet """
        crp = self._crp if self._crp != 'TechLife' else  f'TechLife ({self.tech_life})'

        print(f'Loading data from {self.sheet_name}, for {self._case} and {crp}')
        extractor = Extractor(self._data_master_fname, self.sheet_name,
                              self._case, self._crp, self.scenarios)

        print('\tLoading metrics')
        for metric, var_name in self.metrics:
            if var_name == 'df_cff':
                self.df_cff = self._load_cff(extractor, metric)
            else:
                temp = extractor.get_metric_values(metric, self.num_tds, self.split_metrics)
                setattr(self, var_name, temp)

        if self.has_tax_credit:
            self.df_tc = extractor.get_tax_credits()

        # Pull financial assumptions from small table at top of tech sheet
        print('\tLoading assumptions')
        if self.has_fin_assump:
            self.df_fin = extractor.get_fin_assump()

        if self.has_lcoe_and_wacc:
            print('\tLoading WACC data')
            self.df_wacc, self.df_just_wacc = extractor.get_wacc(self.wacc_name)

        print('\tDone loading data')
        return extractor

    def _load_cff(self, extractor, cff_name):
        """
        Load CFF data from spreadsheet and duplicate for all tech details

        @param {Extractor} extractor - spreadsheet extractor instance
        @param {str} cff_name - name of CFF data in SS
        @returns {pd.DataFrame} - CFF dataframe
        """
        df_cff = extractor.get_cff(cff_name, len(self.scenarios))
        assert len(df_cff) == len(self.scenarios),\
            (f'Wrong number of CFF rows found. Expected {len(self.scenarios)}, '
            f'get {len(df_cff)}.')

        # CFF only has values for the three scenarios. Duplicate for all tech details
        full_df_cff = pd.DataFrame()
        for _ in range(self.num_tds):
            full_df_cff = pd.concat([full_df_cff, df_cff])
        full_df_cff.index = getattr(self, self.metrics[0][1]).index

        return full_df_cff

    def _calc_aep(self):
        assert self.df_ncf is not None, 'NCF must to loaded to calculate AEP'
        df_aep = self.df_ncf * 8760
        return df_aep

    def _calc_capex(self):
        assert self.df_cff is not None and self.df_occ is not None and\
            self.df_gcc is not None, 'CFF, OCC, and GCC must to loaded to calculate CAPEX'
        df_capex = self.df_cff * (self.df_occ + self.df_gcc)
        df_capex = df_capex.copy()
        return df_capex

    def _calc_con_fin_cost(self):
        df_cfc = (self.df_cff - 1) * (self.df_occ + self.df_gcc)
        df_cfc = df_cfc.copy()
        return df_cfc

    def _calc_crf(self):
        crp = self.df_fin.loc['Capital Recovery Period (Years)', 'Value']
        assert isinstance(crp, int) or isinstance(crp, float),\
            f'CRP must be a number, got "{crp}"'

        df_crf = self.df_just_wacc/(1-(1/(1+self.df_just_wacc))**crp)

        # Relabel WACC index as CRF
        df_crf = df_crf.reset_index()
        df_crf['WACC Type'] = df_crf['WACC Type'].apply(lambda x: 'Capital Recovery Factor (CRF)'+x[4:])
        df_crf = df_crf.loc[df_crf['WACC Type'].str.contains('Real')]
        df_crf = df_crf.set_index('WACC Type')

        return df_crf

    def _calc_itc(self, type=''):
        """
        Calculate ITC if used

        @param {str} type - type of ITC to search for (used for utility PV + batt)
        @returns {np.ndarray|int} - array of ITC values or 0
        """
        if self.has_itc:
            itc_index = f'ITC Schedule{type}/*'
            assert itc_index in self.df_tc.index, ('ITC schedule not found in '
                f'tax credit data. Looking for "{itc_index}" in:\n{self.df_tc}')
            df_itc_schedule = self.df_tc.loc[itc_index]
            itc_schedule = df_itc_schedule.values
        else:
            itc_schedule = 0

        return itc_schedule

    def _calc_pff(self, itc_type=''):
        """
        Calculate PFF

        @param {str} itc_type - type of ITC to search for (used for utility PV + batt)
        @returns {pd.DataFrame} - dataframe of PFF
        """
        df_tax_rate = self.df_wacc.loc['Tax Rate (Federal and State)']
        MACRS_schedule = self.depreciation_schedule
        dep_years = len(MACRS_schedule)
        inflation = self.df_wacc.loc['Inflation Rate']

        df_pvd = pd.DataFrame(columns=YEARS)
        for scenario in self.scenarios:
            df_depreciation_factor = pd.DataFrame(columns=YEARS)
            wacc_real = self.df_wacc.loc['WACC Real - ' + scenario]

            for year in range(dep_years):
                df_depreciation_factor.loc[year+1] = 1/((1+wacc_real)*(1+inflation))**(year+1)

            for year in YEARS:
                df_pvd.loc['PVD - ' + scenario,year] = np.dot(MACRS_schedule, df_depreciation_factor[year])

        itc_schedule = self._calc_itc(type=itc_type)

        df_pff = (1 - df_tax_rate.values*df_pvd*(1-itc_schedule/2) - itc_schedule)/(1-df_tax_rate.values)
        df_pff.index = [f'PFF - {scenario}' for scenario in self.scenarios]

        return df_pff

    def _calc_ptc(self):
        """
        Calculate PTC if used

        @returns {np.ndarray|int} - array of PTC values or 0
        """
        if self.has_ptc:
            df_tax_credit = self.df_tc.reset_index()
            df_ptc = df_tax_credit.loc[df_tax_credit['Tax Credit'].str.contains('PTC/', na=False)]

            assert len(df_ptc) != 0, f'PTC data is missing for {self.sheet_name}'
            assert len(df_ptc) == len(self.scenarios), f'Wrong amount of PTC data for{self.sheet_name}'

            df_ptc = pd.concat([df_ptc] * self.num_tds).set_index('Tax Credit')
            ptc = df_ptc.values
        else:
            ptc = 0

        return ptc

    def _calc_lcoe(self):
        ptc = self._calc_ptc()

        assert len(self.df_crf) == len(self.scenarios),\
            (f'CRF has {len(self.df_crf)} rows ({self.df_crf.index}), but there '
             f'are {len(self.scenarios)} scenarios ({self.scenarios})')

        x = self.df_crf.values * self.df_pff
        y = pd.concat([x] * self.num_tds)

        df_lcoe = (1000 * (y.values * self.df_capex.values + self.df_fom)/
                self.df_aep.values)
        df_lcoe = df_lcoe + self.df_vom.values - ptc

        return df_lcoe