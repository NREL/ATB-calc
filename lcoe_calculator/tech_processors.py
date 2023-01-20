"""
Individual tech scrapers. See documentation in base_processor.py.
"""
import pandas as pd

from extractor import TECH_DETAIL_SCENARIO_COL, BASE_YEAR
from macrs import MACRS_6, MACRS_16, MACRS_21
from base_processor import TechProcessor


class OffShoreWindProc(TechProcessor):
    tech_name = 'OffShoreWind'
    sheet_name = 'Offshore Wind'
    depreciation_schedule = MACRS_6
    tech_life = 30
    num_tds = 14
    has_ptc = False
    has_itc = True


class LandBasedWindProc(TechProcessor):
    tech_name = 'LandbasedWind'
    sheet_name = 'Land-Based Wind'
    depreciation_schedule = MACRS_6
    tech_life = 30
    num_tds = 10
    has_ptc = True
    has_itc = False


class DistributedWindProc(TechProcessor):
    tech_name = 'DistributedWind'
    sheet_name = 'Distributed Wind'
    depreciation_schedule = MACRS_6
    tech_life = 30
    num_tds = 40
    has_ptc = True
    has_itc = False


class UtilityPvProc(TechProcessor):
    tech_name = 'UtilityPV'
    tech_life = 30
    sheet_name = 'Solar - Utility PV'
    depreciation_schedule = MACRS_6
    num_tds = 10
    has_ptc = False
    has_itc = True


class CommPvProc(TechProcessor):
    tech_name = 'CommPV'
    tech_life = 30
    sheet_name = 'Solar - PV Dist. Comm'
    depreciation_schedule = MACRS_6
    num_tds = 10
    has_ptc = False
    has_itc = True


class ResPvProc(TechProcessor):
    tech_name = 'ResPV'
    tech_life = 30
    sheet_name = 'Solar - PV Dist. Res'
    depreciation_schedule = MACRS_6
    num_tds = 10
    has_ptc = False
    has_itc = True


class UtilityPvPlusBatteryProc(TechProcessor):
    tech_name = 'Utility-Scale PV-Plus-Battery'
    tech_life = 30
    sheet_name = 'Utility-Scale PV-Plus-Battery'
    wacc_name = 'Solar - Utility PV'  # Use solar PV WACC values
    depreciation_schedule = MACRS_6
    num_tds = 10
    has_ptc = False
    has_itc = True

    GRID_ROUNDTRIP_EFF = 0.85 # Roundtrip Efficiency (Grid charging)

    metrics = [
        ('Net Capacity Factor (%)', 'df_ncf'),
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('PV System Cost ($/kW)', 'df_pv_cost'),
        ('Battery Storage  Cost ($/kW)', 'df_batt_cost'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    def _calc_lcoe(self):
        batt_charge_frac = self.df_fin.loc['Fraction of Battery Energy Charged from PV (75% to 100%)', 'Value']
        grid_charge_cost = self.df_fin.loc['Average Cost of Battery Energy Charged from Grid ($/MWh)', 'Value']

        fcr_pv = pd.concat([self.df_crf.values * self.df_pff_pv] * self.num_tds).values
        fcr_batt = pd.concat([self.df_crf.values * self.df_pff_batt] * self.num_tds).values

        df_lcoe_part = (fcr_pv * self.df_cff * (self.df_pv_cost * 1 + self.df_gcc))\
                       + (fcr_batt * self.df_cff * (self.df_batt_cost * 1 + self.df_gcc))\
                       + self.df_fom
        df_lcoe = (df_lcoe_part * 1000 / self.df_aep)\
                  + self.df_vom\
                  + (1 - batt_charge_frac) * grid_charge_cost / self.GRID_ROUNDTRIP_EFF

        return df_lcoe

    def run(self):
        """ Run all calculations """
        self.df_aep = self._calc_aep()
        self.df_capex = self._calc_capex()
        self.df_cfc = self._calc_con_fin_cost()

        self.df_crf = self._calc_crf()
        self.df_pff_pv = self._calc_pff(itc_type=' - PV')
        self.df_pff_batt = self._calc_pff(itc_type=' - Battery')
        self.df_lcoe = self._calc_lcoe()

class CspProc(TechProcessor):
    tech_name = 'CSP'
    tech_life = 30
    sheet_name = 'Solar - CSP'
    depreciation_schedule = MACRS_6
    num_tds = 3
    has_ptc = False
    has_itc = True


class GeothermalProc(TechProcessor):
    tech_name = 'Geothermal'
    sheet_name = 'Geothermal'
    depreciation_schedule = MACRS_6
    tech_life = 30
    num_tds = 6
    has_ptc = True
    has_itc = True

    def _load_cff(self, extractor, cff_name):
        """
        Special Geothermal code to load CFF and duplicate for tech details

        @param {Extractor} extractor - spreadsheet extractor instance
        @param {str} cff_name - name of CFF data in SS
        @returns {pd.DataFrame} - CFF dataframe
        """
        df_cff = extractor.get_cff(cff_name, len(self.scenarios) * 2)
        assert len(df_cff) == len(self.scenarios * 2),\
            (f'Wrong number of CFF rows found. Expected {len(self.scenarios) * 2}, '
            f'get {len(df_cff)}.')

        hydro = df_cff.iloc[0:3]
        egs = df_cff.iloc[3:6]

        full_df_cff = pd.concat([hydro, hydro, egs, egs, egs, egs])
        full_df_cff.index = getattr(self, self.metrics[0][1]).index
        assert len(full_df_cff) == self.num_tds * len(self.scenarios)

        return full_df_cff

    def OLD_calc_cff(self):
        """
         For 2022 we are scraping CFF from the spreadsheet using the above
         function (_load_cff). This function includes an implementation that
         calculated CFF based on an old spreadsheet format. We may return these
         calculations to Python in future years
         """
        # OLD_TODO: check these labels with Sertac, might need to update the year
        df_fin = self.df_fin
        import pdb; pdb.set_trace()

        # OLD_TODO - fix the -Hydro typo in excel
        cff_start_hydro = df_fin.loc['Construction Finance Factor (2018 -Hydro)','Value']
        cff_end_mod_hydro = df_fin.loc['Construction Finance Factor (Moderate 2030 - Hydro)','Value']
        cff_end_adv_hydro = df_fin.loc['Construction Finance Factor (Advanced 2030 - Hydro)','Value']
        cff_start_egs = df_fin.loc['Construction Finance Factor (2018 - EGS)','Value']
        cff_end_mod_egs = df_fin.loc['Construction Finance Factor (Moderate 2030 - EGS)','Value']
        cff_end_adv_egs = df_fin.loc['Construction Finance Factor (Advanced 2030 - EGS)','Value']

        # Programatically construct column names
        tech_details = ['Hydro / Flash', 'Hydro / Binary', 'NF EGS / Flash',
                        'NF EGS / Binary', 'Deep EGS / Flash', 'Deep EGS / Binary']

        cff_end_dict_hydro = {
            self.scenarios[0]: cff_end_adv_hydro,
            self.scenarios[1]: cff_end_mod_hydro,
            self.scenarios[2]: cff_start_hydro
        }

        cff_end_dict_egs = {
            self.scenarios[0]: cff_end_adv_egs,
            self.scenarios[1]: cff_end_mod_egs,
            self.scenarios[2]: cff_start_egs
        }

        cols = []
        start_data = []
        end_data = []
        for detail in tech_details:
            for scenario in self.scenarios:
                cols.append(detail + ' - ' + scenario)
                if ('Hydro' in detail):
                    start_data.append(cff_start_hydro)
                    end_data.append(cff_end_dict_hydro[scenario])
                elif ('EGS' in detail):
                    start_data.append(cff_start_egs)
                    end_data.append(cff_end_dict_egs[scenario])

        # Create NaN columns to fill with interpolation later
        early_years = range(BASE_YEAR-1, 2030, 1)
        df_cff_linear = pd.DataFrame(index=cols, columns=early_years, dtype=float)
        df_cff_linear.insert(0, 2018, start_data)
        df_cff_linear.insert(len(early_years) + 1, 2030, end_data)
        df_cff_linear.interpolate(inplace=True, axis=1)

        # 2021 sheets still includes 2018 in CFF calculations, drop it for multiplication later
        df_cff_linear.drop(2018, axis=1, inplace=True)

        late_years = range(2031, 2051, 1)
        for year in late_years:
            df_cff_linear.insert(len(df_cff_linear.columns), year, end_data)

        df_cff_linear.index.rename(TECH_DETAIL_SCENARIO_COL, inplace=True)
        return df_cff_linear


class HydropowerProc(TechProcessor):
    tech_name = 'Hydropower'
    sheet_name = 'Hydropower'
    depreciation_schedule = MACRS_21
    tech_life = 100
    num_tds = 12
    has_ptc = True
    has_itc = False
    split_metrics = True


class PumpedStorageHydroProc(TechProcessor):
    tech_name = 'Pumped Storage Hydropower'
    sheet_name = 'Pumped Storage Hydropower'
    wacc_name = 'Hydropower'  # Use hydropower WACC values for pumped storage
    depreciation_schedule = MACRS_21
    tech_life = 100
    num_tds = 15
    has_ptc = False
    has_itc = False

    metrics = [
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    def run(self):
        """ Run all calculations """
        self.df_capex = self._calc_capex()
        self.df_cfc = self._calc_con_fin_cost()

    def test_lcoe(self):
        pass


class CoalProc(TechProcessor):
    tech_name = 'Coal_FE'
    tech_life = 75

    metrics = [
        ('Heat Rate  (MMBtu/MWh)', 'df_hr'),
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    flat_attrs = [
        ('df_hr', 'Heat Rate'),
        ('df_occ', 'OCC'),
        ('df_gcc', 'GCC'),
        ('df_fom', 'Fixed O&M'),
        ('df_vom', 'Variable O&M'),
        ('df_cfc', 'CFC'),
        ('df_capex', 'CAPEX'),
    ]

    sheet_name = 'Coal_FE'
    depreciation_schedule = MACRS_21
    num_tds = 4
    has_ptc = False
    has_itc = False
    has_tax_credit = False

    def run(self):
        """ Run all calculations except LCOE """
        self.df_capex = self._calc_capex()
        self.df_cfc = self._calc_con_fin_cost()

    def test_lcoe(self):
        pass


class NaturalGasProc(TechProcessor):
    tech_name = 'NaturalGas_FE'
    tech_life = 55

    metrics = [
        ('Heat Rate  (MMBtu/MWh)', 'df_hr'),
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    flat_attrs = [
        ('df_hr', 'Heat Rate'),
        ('df_occ', 'OCC'),
        ('df_gcc', 'GCC'),
        ('df_fom', 'Fixed O&M'),
        ('df_vom', 'Variable O&M'),
        ('df_cfc', 'CFC'),
        ('df_capex', 'CAPEX'),
    ]
    sheet_name = 'Natural Gas_FE'
    depreciation_schedule = MACRS_16
    num_tds = 7
    has_ptc = False
    has_itc = False
    has_tax_credit = False

    def run(self):
        """ Run all calculations except LCOE """
        self.df_capex = self._calc_capex()
        self.df_cfc = self._calc_con_fin_cost()

    def test_lcoe(self):
        pass

class NuclearProc(TechProcessor):
    tech_name = 'Nuclear'
    tech_life = 60
    sheet_name = 'Nuclear'
    depreciation_schedule = MACRS_16
    num_tds = 2
    scenarios = ['Moderate']
    has_ptc = False
    has_itc = False

    metrics = [
        ('Heat Rate  (MMBtu/MWh)', 'df_hr'),
        ('Net Capacity Factor (%)', 'df_ncf'),
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('Fuel Costs ($/MMBtu)', 'df_fuel_costs_mmbtu'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    flat_attrs = [
        ('df_ncf', 'CF'),
        ('df_occ', 'OCC'),
        ('df_gcc', 'GCC'),
        ('df_fom', 'Fixed O&M'),
        ('df_vom', 'Variable O&M'),
        ('df_cfc', 'CFC'),
        ('df_lcoe', 'LCOE'),
        ('df_capex', 'CAPEX'),
        ('df_fuel_costs_mwh', 'Fuel'),
    ]

    def _calc_crf(self):
        """
        Nuclear only has one scenario, extract the correct CRF.
        """
        # TODO - automatically determine numeber of CRFs needed for tech
        # scenarios in TechProcessor._calc_crf()
        assert self.scenarios == ['Moderate']
        df_crf = super()._calc_crf()
        df_crf = df_crf[df_crf.index == 'Capital Recovery Factor (CRF) Real - Moderate']
        return df_crf

    def _calc_lcoe(self):
        """ Include fuel costs in LCOE """
        self.df_fuel_costs_mwh = self.df_hr * self.df_fuel_costs_mmbtu
        df_lcoe = super()._calc_lcoe() + self.df_fuel_costs_mwh
        return df_lcoe


class BiopowerProc(TechProcessor):
    tech_name = 'Biopower'
    tech_life = 45
    sheet_name = 'Biopower'
    depreciation_schedule = MACRS_6
    num_tds = 1
    has_ptc = False
    has_itc = False

    metrics = [
        ('Heat Rate  (MMBtu/MWh)', 'df_hr'),
        ('Net Capacity Factor (%)', 'df_ncf'),
        ('Overnight Capital Cost ($/kW)', 'df_occ'),
        ('Grid Connection Costs (GCC) ($/kW)', 'df_gcc'),
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
        ('Fuel Costs ($/MMBtu)', 'df_fuel_costs_mmbtu'),
        ('Construction Finance Factor', 'df_cff'),
    ]

    flat_attrs = [
        ('df_ncf', 'CF'),
        ('df_occ', 'OCC'),
        ('df_gcc', 'GCC'),
        ('df_fom', 'Fixed O&M'),
        ('df_vom', 'Variable O&M'),
        ('df_cfc', 'CFC'),
        ('df_lcoe', 'LCOE'),
        ('df_capex', 'CAPEX'),
        ('df_fuel_costs_mwh', 'Fuel'),
    ]

    def _calc_lcoe(self):
        """ Include fuel costs in LCOE """
        self.df_fuel_costs_mwh = self.df_hr * self.df_fuel_costs_mmbtu
        df_lcoe = super()._calc_lcoe() + self.df_fuel_costs_mwh
        return df_lcoe


class UtilityBatteryProc(TechProcessor):
    tech_name = 'Utility-Scale Battery Storage'
    tech_life = 30
    sheet_name = 'Utility-Scale Battery Storage'
    depreciation_schedule = MACRS_6
    num_tds = 5
    has_lcoe_and_wacc = False
    has_fin_assump = False
    has_tax_credit = False
    has_ptc = False
    has_itc = True

    metrics = [
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
    ]

    def run(self):
        """ No calcs needed for batteries """
        pass

    def test_capex(self):
        pass


class CommBatteryProc(TechProcessor):
    tech_name = 'Commercial Battery Storage'
    tech_life = 30
    sheet_name = 'Commercial Battery Storage'
    depreciation_schedule = MACRS_6
    num_tds = 5
    has_lcoe_and_wacc = False
    has_fin_assump = False
    has_tax_credit = False
    has_ptc = False
    has_itc = True

    metrics = [
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
    ]

    def run(self):
        """ No calcs needed for batteries"""
        pass
    
    def test_capex(self):
        pass

class ResBatteryProc(TechProcessor):
    tech_name = 'Residential Battery Storage'
    tech_life = 30
    sheet_name = 'Residential Battery Storage'
    depreciation_schedule = MACRS_6
    num_tds = 2
    has_lcoe_and_wacc = False
    has_fin_assump = False
    has_tax_credit = False
    has_ptc = False
    has_itc = True

    metrics = [
        ('Fixed Operation and Maintenance Expenses ($/kW-yr)', 'df_fom'),
        ('Variable Operation and Maintenance Expenses ($/MWh)', 'df_vom'),
    ]

    def run(self):
        """ No calcs needed for batteries"""
        pass

    def test_capex(self):
        pass