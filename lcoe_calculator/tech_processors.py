#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Individual tech processors. See documentation in base_processor.py.
"""
from typing import List, Optional, Type
import numpy as np
import pandas as pd

from lcoe_calculator.abstract_extractor import AbstractExtractor

from .config import MARKET_FIN_CASE, CrpChoiceType
from .extractor import Extractor
from .tech_extractors import PVBatteryExtractor
from .macrs import MACRS_6, MACRS_16, MACRS_21
from .base_processor import TechProcessor


class OffShoreWindProc(TechProcessor):
    """
    Abstract class, sheet name is not defined. See Fixed and Floating OSW proc
    """

    tech_name = "OffShoreWind"
    tech_life = 30
    dscr = 1.35


class FixedOffShoreWindProc(OffShoreWindProc):
    sheet_name = "Fixed-Bottom Offshore Wind"
    num_tds = 7
    default_tech_detail = "Offshore Wind - Class 3"
    wacc_name = "Offshore Wind"


class FloatingOffShoreWindProc(OffShoreWindProc):
    sheet_name = "Floating Offshore Wind"
    num_tds = 7
    base_year = 2030
    default_tech_detail = "Offshore Wind - Class 12"
    wacc_name = "Offshore Wind"


class LandBasedWindProc(TechProcessor):
    tech_name = "LandbasedWind"
    sheet_name = "Land-Based Wind"
    tech_life = 30
    num_tds = 10
    default_tech_detail = "Land-Based Wind - Class 4 - Technology 1"
    dscr = 1.35


class DistributedWindProc(TechProcessor):
    tech_name = "DistributedWind"
    sheet_name = "Distributed Wind"
    tech_life = 30
    num_tds = 40
    default_tech_detail = "Midsize DW - Class 4"
    dscr = 1.35


class UtilityPvProc(TechProcessor):
    tech_name = "UtilityPV"
    tech_life = 30
    sheet_name = "Solar - Utility PV"
    num_tds = 10
    default_tech_detail = "Utility PV - Class 5"
    dscr = 1.25


class CommPvProc(TechProcessor):
    tech_name = "CommPV"
    tech_life = 30
    sheet_name = "Solar - PV Dist. Comm"
    num_tds = 10
    default_tech_detail = "Commercial PV - Class 5"
    dscr = 1.25


class ResPvProc(TechProcessor):
    tech_name = "ResPV"
    tech_life = 30
    sheet_name = "Solar - PV Dist. Res"
    num_tds = 10
    default_tech_detail = "Residential PV - Class 5"
    dscr = 1.25


class UtilityPvPlusBatteryProc(TechProcessor):
    tech_name = "Utility-Scale PV-Plus-Battery"
    tech_life = 30
    sheet_name = "Utility-Scale PV-Plus-Battery"
    num_tds = 10
    default_tech_detail = "PV+Storage - Class 5"
    dscr = 1.25

    GRID_ROUNDTRIP_EFF = 0.85  # Roundtrip Efficiency (Grid charging)
    CO_LOCATION_SAVINGS = 0.9228  # Reduction in OCC from co-locating the PV and battery system on the same site
    BATT_PV_RATIO = (
        60.0 / 100.0
    )  # Modifier for $/kW to get everything on the same basis

    metrics = [
        ("Net Capacity Factor (%)", "df_ncf"),
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("PV System Cost ($/kW)", "df_pv_cost"),
        ("Battery Storage  Cost ($/kW)", "df_batt_cost"),
        ("Construction Finance Factor", "df_cff"),
        ("PV-only Capacity Factor (%)", "df_pvcf"),
    ]

    def __init__(
        self,
        data_workbook_fname: str,
        case: str = MARKET_FIN_CASE,
        crp: CrpChoiceType = 30,
        tcc: str = "PV PTC and Battery ITC",
        extractor: Type[PVBatteryExtractor] = PVBatteryExtractor,
    ):
        # Additional data frames pulled from excel
        self.df_pv_cost: Optional[pd.DataFrame] = None
        self.df_batt_cost: Optional[pd.DataFrame] = None

        super().__init__(data_workbook_fname, case, crp, tcc, extractor)

    def _calc_lcoe(self):
        batt_charge_frac = self.df_fin.loc[
            "Fraction of Battery Energy Charged from PV (75% to 100%)", "Value"
        ]
        grid_charge_cost = self.df_fin.loc[
            "Average Cost of Battery Energy Charged from Grid ($/MWh)", "Value"
        ]

        ptc = self._calc_ptc()
        ptc_cf_adj = self.df_pvcf / self.df_ncf
        ptc_cf_adj = ptc_cf_adj.clip(
            upper=1.0
        )  # account for RTE losses at 100% grid charging (might need to make equation above better)

        fcr_pv = pd.concat([self.df_crf.values * self.df_pff_pv] * self.num_tds).values
        fcr_batt = pd.concat(
            [self.df_crf.values * self.df_pff_batt] * self.num_tds
        ).values

        df_lcoe_part = (
            (
                fcr_pv
                * self.df_cff
                * (self.df_pv_cost * self.CO_LOCATION_SAVINGS + self.df_gcc)
            )
            + (
                fcr_batt
                * self.df_cff
                * (self.df_batt_cost * self.CO_LOCATION_SAVINGS * self.BATT_PV_RATIO)
            )
            + self.df_fom
        )
        df_lcoe = (
            (df_lcoe_part * 1000 / self.df_aep)
            + self.df_vom
            + (1 - batt_charge_frac) * grid_charge_cost / self.GRID_ROUNDTRIP_EFF
            - ptc * ptc_cf_adj
        )

        return df_lcoe

    def _extract_data(self):
        """Pull all data from the workbook"""
        crp_msg = (
            self._requested_crp
            if self._requested_crp != "TechLife"
            else f"TechLife ({self.tech_life})"
        )

        print(f"Loading data from {self.sheet_name}, for {self._case} and {crp_msg}")
        extractor = self._ExtractorClass(
            self._data_workbook_fname,
            self.sheet_name,
            self._case,
            self._requested_crp,
            self.scenarios,
            self.base_year,
            self.tax_credit_case,
        )

        print("\tLoading metrics")
        for metric, var_name in self.metrics:
            if var_name == "df_cff":
                # Grab DF index from another value to use in full CFF DF
                index = getattr(self, self.metrics[0][1]).index
                self.df_cff = self.load_cff(extractor, metric, index)
                continue

            temp = extractor.get_metric_values(metric, self.num_tds, self.split_metrics)
            setattr(self, var_name, temp)

        if self.has_tax_credit:
            self.df_tc = extractor.get_tax_credits()

        # Pull financial assumptions from small table at top of tech sheet
        print("\tLoading assumptions")
        if self.has_fin_assump:
            self.df_fin = extractor.get_fin_assump()

        if self.has_wacc:
            print("\tLoading WACC data")
            self.df_wacc, self.df_just_wacc = extractor.get_wacc(self.wacc_name)

        print("\tDone loading data")
        return extractor

    def _get_tax_credit_case(self):
        """
        Incorporates additional code required to handle different tax credits for
        different components. PV plus Battery worksheet has additional lines for
        battery ITC.
        """
        assert (
            len(self.df_tc) > 0
        ), "Setup df_tc with extractor.get_tax_credits() before calling this function!"

        ptc = self._calc_ptc()
        # Battery always takes ITC, so PV determines the case
        pv_itc = self._calc_itc(itc_type=" - PV")
        batt_itc = self._calc_itc(itc_type=" - Battery")

        # Trim the first year to eliminate pre-inflation reduction act confusion
        ptc = ptc[:, 1:]
        pv_itc = pv_itc[1:]
        batt_itc = batt_itc[1:]

        ptc_sum = np.sum(ptc)
        pv_itc_sum = np.sum(pv_itc)
        batt_itc_sum = np.sum(batt_itc)

        if ptc_sum > 0 and batt_itc_sum > 0:
            return "PTC + ITC"
        elif pv_itc_sum > 0 and batt_itc_sum > 0:
            return "ITC"
        elif ptc_sum > 0:
            return "PTC"
        else:
            return "None"

    def run(self):
        """Run all calculations"""
        self.df_aep = self._calc_aep()
        self.df_capex = self._calc_capex()
        self.df_cfc = self._calc_con_fin_cost()

        self.df_crf = self._calc_crf()
        self.df_pff_pv = self._calc_pff(itc_type=" - PV")
        self.df_pff_batt = self._calc_pff(itc_type=" - Battery")
        self.df_lcoe = self._calc_lcoe()


class CspProc(TechProcessor):
    tech_name = "CSP"
    tech_life = 30
    sheet_name = "Solar - CSP"
    num_tds = 3
    default_tech_detail = "CSP - Class 2"
    dscr = 1.45


class GeothermalProc(TechProcessor):
    tech_name = "Geothermal"
    sheet_name = "Geothermal"
    tech_life = 30
    num_tds = 6
    default_tech_detail = "Geothermal - Hydro / Flash"
    dscr = 1.35

    @classmethod
    def load_cff(
        cls, extractor: Extractor, cff_name: str, index: pd.Index, return_short_df=False
    ) -> pd.DataFrame:
        """
        Special Geothermal code to load CFF and duplicate for tech details. Geothermal has
        6 rows of CFF instead of the normal 3.

        @param extractor - workbook extractor instance
        @param cff_name - name of CFF data in SS
        @param index - Index of a "normal" data frame for this tech to use for df_cff
        @param return_short_df - return original 6 row data frame if True
        @returns - CFF data frame
        """
        df_cff = extractor.get_cff(cff_name, len(cls.scenarios) * 2)
        assert len(df_cff) == len(cls.scenarios * 2), (
            f"Wrong number of CFF rows found. Expected {len(cls.scenarios) * 2}, "
            f"get {len(df_cff)}."
        )

        if return_short_df:
            return df_cff

        hydro = df_cff.iloc[0:3]
        egs = df_cff.iloc[3:6]

        full_df_cff = pd.concat([hydro, hydro, egs, egs, egs, egs])
        full_df_cff.index = index
        assert len(full_df_cff) == cls.num_tds * len(cls.scenarios)

        return full_df_cff


class HydropowerProc(TechProcessor):
    tech_name = "Hydropower"
    sheet_name = "Hydropower"
    tech_life = 100
    num_tds = 12
    split_metrics = True
    default_tech_detail = "Hydropower - NPD 1"
    dscr = 1.35

    def get_depreciation_schedule(self, year):
        if self._case is MARKET_FIN_CASE and (year < 2025):
            return MACRS_21
        else:
            return MACRS_6


class PumpedStorageHydroProc(TechProcessor):
    tech_name = "Pumped Storage Hydropower"
    sheet_name = "Pumped Storage Hydropower"
    wacc_name = "Hydropower"  # Use hydropower WACC values for pumped storage
    tech_life = 100
    num_tds = 15
    has_tax_credit = False
    has_lcoe = False

    flat_attrs = [
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_capex", "CAPEX"),
    ]

    metrics = [
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Construction Finance Factor", "df_cff"),
    ]


class PumpedStorageHydroOneResProc(PumpedStorageHydroProc):
    sheet_name = "PSH One New Res"
    num_tds = 5


class CoalProc(TechProcessor):
    tech_name = "Coal_FE"
    tech_life = 75

    metrics = [
        ("Heat Rate (MMBtu/MWh)", "df_hr"),
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Construction Finance Factor", "df_cff"),
    ]

    flat_attrs = [
        ("df_hr", "Heat Rate"),
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_capex", "CAPEX"),
    ]

    sheet_name = "Coal_FE"
    num_tds = 5
    has_tax_credit = False
    has_lcoe = False
    default_tech_detail = "Coal-95%-CCS"
    dscr = 1.45
    _depreciation_schedule = MACRS_21


class NaturalGasProc(TechProcessor):
    tech_name = "NaturalGas_FE"
    tech_life = 55

    metrics = [
        ("Heat Rate (MMBtu/MWh)", "df_hr"),
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Construction Finance Factor", "df_cff"),
    ]

    flat_attrs = [
        ("df_hr", "Heat Rate"),
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_capex", "CAPEX"),
    ]
    sheet_name = "Natural Gas_FE"
    num_tds = 10
    has_tax_credit = False
    has_lcoe = False
    default_tech_detail = "NG F-Frame CC 95% CCS"
    dscr = 1.45
    _depreciation_schedule = MACRS_21


class NaturalGasFuelCellProc(NaturalGasProc):
    sheet_name = "Natural Gas Fuel Cell_FE"
    num_tds = 2
    has_wacc = False
    has_lcoe = False
    has_fin_assump = False
    default_tech_detail = "NG Fuel Cell Max CCS"

    scenarios = ["Moderate", "Advanced"]
    base_year = 2035


class CoalRetrofitProc(TechProcessor):
    tech_name = "Coal_Retrofits"
    tech_life = 75

    has_wacc = False
    has_lcoe = False
    has_capex = False
    has_fin_assump = False

    metrics = [
        ("Heat Rate (MMBtu/MWh)", "df_hr"),
        ("Additional Overnight Capital Cost ($/kW)", "df_occ"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Heat Rate Penalty (Δ% from pre-retrofit)", "df_hrp"),
        ("Net Output Penalty (Δ% from pre-retrofit)", "df_nop"),
    ]

    flat_attrs = [
        ("df_hr", "Heat Rate"),
        ("df_occ", "Additional OCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_hrp", "Heat Rate Penalty"),
        ("df_nop", "Net Output Penalty"),
    ]

    sheet_name = "Coal_Retrofits"
    num_tds = 2
    has_tax_credit = False


class NaturalGasRetrofitProc(TechProcessor):
    tech_name = "NaturalGas_Retrofits"
    tech_life = 55

    has_wacc = False
    has_lcoe = False
    has_capex = False
    has_fin_assump = False

    metrics = [
        ("Heat Rate (MMBtu/MWh)", "df_hr"),
        ("Additional Overnight Capital Cost ($/kW)", "df_occ"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Heat Rate Penalty (Δ% from pre-retrofit)", "df_hrp"),
        ("Net Output Penalty (Δ% from pre-retrofit)", "df_nop"),
    ]

    flat_attrs = [
        ("df_hr", "Heat Rate"),
        ("df_occ", "Additional OCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_hrp", "Heat Rate Penalty"),
        ("df_nop", "Net Output Penalty"),
    ]

    sheet_name = "Natural Gas_Retrofits"
    num_tds = 4
    has_tax_credit = False


class NuclearProc(TechProcessor):
    tech_name = "Nuclear"
    tech_life = 60
    sheet_name = "Nuclear"
    num_tds = 2
    default_tech_detail = "Nuclear - Large"
    dscr = 1.45
    base_year = 2030

    metrics = [
        ("Heat Rate (MMBtu/MWh)", "df_hr"),
        ("Net Capacity Factor (%)", "df_ncf"),
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Fuel Costs ($/MMBtu)", "df_fuel_costs_mmbtu"),
        ("Construction Finance Factor", "df_cff"),
    ]

    flat_attrs = [
        ("df_ncf", "CF"),
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_lcoe", "LCOE"),
        ("df_capex", "CAPEX"),
        ("df_fuel_costs_mwh", "Fuel"),
        ("df_hr", "Heat Rate"),
    ]

    @classmethod
    def load_cff(
        cls, extractor: Extractor, cff_name: str, index: pd.Index, return_short_df=False
    ) -> pd.DataFrame:
        """
        Load CFF data from workbook. Nuclear has a unique CFF for each tech detail,
        so this function removes the tech detail duplication code from BaseProcessor.
        """
        df_cff = extractor.get_cff(cff_name, len(cls.scenarios) * cls.num_tds)
        # Rename CFF index to match other tech details
        df_cff.index = index

        return df_cff

    def _calc_lcoe(self):
        """Include fuel costs in LCOE"""
        # pylint: disable=no-member,attribute-defined-outside-init
        self.df_fuel_costs_mwh = self.df_hr * self.df_fuel_costs_mmbtu
        df_lcoe = super()._calc_lcoe() + self.df_fuel_costs_mwh
        return df_lcoe

    def get_depreciation_schedule(self, year):
        if self._case is MARKET_FIN_CASE and (year < 2025):
            return MACRS_16
        else:
            return MACRS_6


class BiopowerProc(TechProcessor):
    tech_name = "Biopower"
    tech_life = 45
    sheet_name = "Biopower"
    num_tds = 1
    default_tech_detail = "Biopower - Dedicated"
    dscr = 1.45

    metrics = [
        ("Heat Rate (MMBtu/MWh)", "df_hr"),
        ("Net Capacity Factor (%)", "df_ncf"),
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Fuel Costs ($/MMBtu)", "df_fuel_costs_mmbtu"),
        ("Construction Finance Factor", "df_cff"),
    ]

    flat_attrs = [
        ("df_ncf", "CF"),
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_lcoe", "LCOE"),
        ("df_capex", "CAPEX"),
        ("df_fuel_costs_mwh", "Fuel"),
        ("df_hr", "Heat Rate"),
    ]

    def _calc_lcoe(self):
        """Include fuel costs in LCOE"""
        # pylint: disable=no-member,attribute-defined-outside-init
        self.df_fuel_costs_mwh = self.df_hr * self.df_fuel_costs_mmbtu
        df_lcoe = super()._calc_lcoe() + self.df_fuel_costs_mwh
        return df_lcoe


# ------------------ Batteries --------------------
class AbstractBatteryProc(TechProcessor):
    """
    Abstract tech processor for batteries w/o LCOE or CAPEX.
    """

    has_wacc = False
    has_lcoe = False

    # This is false because the ATB does not calculate LCOS (batteries can receive the ITC).
    has_tax_credit = False

    metrics = [
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        ("Construction Finance Factor", "df_cff"),
    ]

    flat_attrs = [
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_capex", "CAPEX"),
    ]


class UtilityBatteryProc(AbstractBatteryProc):
    tech_name = "Utility-Scale Battery Storage"
    tech_life = 30
    sheet_name = "Utility-Scale Battery Storage"
    num_tds = 5


class CommBatteryProc(AbstractBatteryProc):
    tech_name = "Commercial Battery Storage"
    tech_life = 30
    sheet_name = "Commercial Battery Storage"
    num_tds = 5


class ResBatteryProc(AbstractBatteryProc):
    tech_name = "Residential Battery Storage"
    tech_life = 30
    sheet_name = "Residential Battery Storage"
    num_tds = 2


ALL_TECHS: List[Type[TechProcessor]] = [
    FixedOffShoreWindProc,
    FloatingOffShoreWindProc,
    LandBasedWindProc,
    DistributedWindProc,
    UtilityPvProc,
    CommPvProc,
    ResPvProc,
    UtilityPvPlusBatteryProc,
    CspProc,
    GeothermalProc,
    HydropowerProc,
    PumpedStorageHydroProc,
    PumpedStorageHydroOneResProc,
    CoalProc,
    NaturalGasProc,
    NuclearProc,
    BiopowerProc,
    UtilityBatteryProc,
    CommBatteryProc,
    ResBatteryProc,
    CoalRetrofitProc,
    NaturalGasRetrofitProc,
    NaturalGasFuelCellProc,
]


# All technologies that have an LCOE
LCOE_TECHS = [Tech for Tech in ALL_TECHS if Tech.has_lcoe]
