#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Tech LCOE and CAPEX processor class. This is effectively an abstract class and must be subclassed.
"""
from typing import List, Tuple, Type, Optional
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np

from .macrs import MACRS_6
from .extractor import Extractor
from .abstract_extractor import AbstractExtractor
from .config import (
    FINANCIAL_CASES,
    END_YEAR,
    TECH_DETAIL_SCENARIO_COL,
    MARKET_FIN_CASE,
    CRP_CHOICES,
    SCENARIOS,
    LCOE_SS_NAME,
    CAPEX_SS_NAME,
    CFF_SS_NAME,
    CrpChoiceType,
    BASE_YEAR,
)


class TechProcessor(ABC):
    """
    Base abstract tech-processor class. This must be sub-classed to be used. See tech_processors.py
    for examples.  Various class vars like sheet_name must be over-written by sub-classes, things
    like tech_life can be as needed. Functions for _calc_capex(), _con_fin_cost(), etc can be
    over-written as needed, e.g. Geothermal.

    Notable methods:

    __init__() - Various class attribute sanity checks and loads data from the workbook.
    run() - Perform all calcs to determine CAPEX and LCOE.
    flat - (property) Convert fin assumptions and values in flat_attrs to a flat DataFrame
    test_lcoe() - Compare calculated LCOE to LCOE in workbook.
    test_capex() - Compare calculated CAPEX to CAPEX in workbook.
    """

    # ----------- These attributes must be set for each tech --------------
    @property
    @abstractmethod
    def sheet_name(self) -> str:
        """Name of the sheet in the excel data workbook"""

    @property
    @abstractmethod
    def tech_name(self) -> str:
        """Name of tech for flat file"""

    # For a consistent depreciation schedule, use one of the lists from the
    # macrs.py file as shown below. More complex schedules can be defined by
    # overloading the get_depreciation_schedule() function. See HydropowerProc
    # in tech_processors.py for an example.
    _depreciation_schedule: List[float] = MACRS_6

    # ------------ All other attributes have defaults -------------------------
    # Metrics to load from SS. Format: (header in SS, object attribute name)
    metrics: List[Tuple[str, str]] = [
        ("Net Capacity Factor (%)", "df_ncf"),
        ("Overnight Capital Cost ($/kW)", "df_occ"),
        ("Grid Connection Costs (GCC) ($/kW)", "df_gcc"),
        ("Fixed Operation and Maintenance Expenses ($/kW-yr)", "df_fom"),
        ("Variable Operation and Maintenance Expenses ($/MWh)", "df_vom"),
        (CFF_SS_NAME, "df_cff"),
    ]

    tech_life = 30  # Tech lifespan in years
    num_tds = 10  # Number of technical resource groups
    scenarios = SCENARIOS
    base_year: int = BASE_YEAR

    has_tax_credit = True  # Does the tech have tax credits in the workbook
    has_fin_assump = True  # Does the tech have financial assumptions in the workbook

    wacc_name: Optional[str] = (
        None  # Name of tech to look for on WACC sheet, use sheet name if None
    )
    has_wacc = True  # If True, pull values from WACC sheet.
    has_capex = True  # If True, calculate CAPEX
    has_lcoe = True  # If True, calculate CRF, PFF, & LCOE.

    split_metrics = (
        False  # Indicates 3 empty rows in tech detail metrics, e.g. hydropower
    )

    # Attributes to export in flat file, format: (attr name in class, value for
    # flat file). Any attributes that are None are silently ignored. Financial
    # assumptions values are added automatically.
    # See https://atb.nrel.gov/electricity/2023/acronyms or below for acronym definitions
    flat_attrs: List[Tuple[str, str]] = [
        ("df_ncf", "CF"),
        ("df_occ", "OCC"),
        ("df_gcc", "GCC"),
        ("df_fom", "Fixed O&M"),
        ("df_vom", "Variable O&M"),
        ("df_cfc", "CFC"),
        ("df_lcoe", "LCOE"),
        ("df_capex", "CAPEX"),
    ]

    # Variables used by the debt fraction calculator. Should be filled out for any tech
    # where self.has_lcoe == True.
    default_tech_detail: Optional[str] = None
    dscr: Optional[float] = (
        None  # Debt service coverage ratio (unitless, typically 1-1.5)
    )

    def __init__(
        self,
        data_workbook_fname: str,
        case: str = MARKET_FIN_CASE,
        crp: CrpChoiceType = 30,
        tcc: Optional[str] = None,
        extractor: Type[AbstractExtractor] = Extractor,
    ):
        """
        @param data_workbook_fname - name of workbook
        @param case - financial case to run: 'Market' or 'R&D'
        @param crp - capital recovery period: 20, 30, or 'TechLife'
        @param tcc - tax credit case: 'ITC only' or 'PV PTC and Battery ITC' Only required for the PV plus battery technology.
        @param extractor - Extractor class to use to obtain source data.
        """
        assert case in FINANCIAL_CASES, (
            f"Financial case must be one of {FINANCIAL_CASES}," f" received {case}"
        )
        assert crp in CRP_CHOICES, (
            f"Financial case must be one of {CRP_CHOICES}," f" received {crp}"
        )
        assert isinstance(self.scenarios, list), "self.scenarios must be a list"

        if self.has_lcoe:
            if self.default_tech_detail is None:
                raise ValueError("default_tech_detail must be set if has_lcoe is True.")
            if self.dscr is None:
                raise ValueError("dscr must be set if has_lcoe is True.")

        self._data_workbook_fname = data_workbook_fname
        self._case = case
        self._requested_crp = crp
        self._crp_years = self.tech_life if crp == "TechLife" else crp
        self._tech_years = range(self.base_year, END_YEAR + 1, 1)

        self.tax_credit_case = tcc

        # These data frames are extracted from excel
        self.df_ncf = None  # Net capacity factor (%)
        self.df_occ = None  # Overnight capital cost ($/kW)
        self.df_gcc = None  # Grid connection costs ($/kW)
        self.df_fom = None  # Fixed O&M ($/kW-yr)
        self.df_vom = None  # Variable O&M ($/MWh)
        self.df_tc = None  # Tax credits (varies)
        self.df_wacc = None  # WACC table (varies)
        self.df_just_wacc = None  # Last six rows of WACC table
        self.df_hrp = None  # Heat Rate Penalty (% change), retrofits only
        self.df_nop = None  # Net Output Penalty (% change), retrofits only
        self.df_pvcf = None  # PV-only capacity factor (%), PV-plus-battery only

        # These data frames are calculated and populated by object methods
        self.df_aep = None  # Annual energy production (kWh/kW)
        self.df_capex = None  # CAPEX ($/kW)
        self.df_cfc = None  # Construction finance cost ($/kW)
        self.df_crf = None  # Capital recovery factor - real (%)
        self.df_pff = None  # Project finance factor (unitless)
        self.df_lcoe = None  # LCOE ($/MWh)

        self._ExtractorClass = extractor
        self._extractor = self._extract_data()

    def run(self):
        """Run all calculations for CAPEX and LCOE"""
        if self.has_capex:
            self.df_cfc = self._calc_con_fin_cost()
            self.df_capex = self._calc_capex()
            assert (
                not self.df_capex.isnull().any().any()
            ), f"Error in calculated CAPEX, found missing values: {self.df_capex}"

        if self.has_lcoe and self.has_wacc:
            self.df_aep = self._calc_aep()
            self.df_crf = self._calc_crf()
            self.df_pff = self._calc_pff()
            self.df_lcoe = self._calc_lcoe()
            assert (
                not self.df_lcoe.isnull().any().any()
            ), f"Error in calculated LCOE, found missing values: {self.df_lcoe}"

    @property
    def flat(self) -> pd.DataFrame:
        """
        Return flattened data, joining all outputs. Split tech detail and
        scenario into separate columns and append tech, parameter name, case and
        crp. Include financial if present. Outputs are defined in self.flat_attrs,
        but are silently skipped if value attribute value is None.

        @returns Flat data for tech
        """
        df_flat = pd.DataFrame() if self.df_wacc is None else self._flat_fin_assump()

        case = self._case.upper()
        if case == "MARKET":
            case = MARKET_FIN_CASE

        for attr, parameter in self.flat_attrs:
            df = getattr(self, attr)
            df = df.reset_index()

            old_cols = df.columns
            df[["DisplayName", "Scenario"]] = df[TECH_DETAIL_SCENARIO_COL].str.rsplit(
                "/", n=1, expand=True
            )
            df.DisplayName = df.DisplayName.str.strip()
            df.Scenario = df.Scenario.str.strip()
            df["Parameter"] = parameter
            df_flat = pd.concat([df_flat, df])

        df_flat["Technology"] = self.tech_name
        df_flat["Case"] = case
        df_flat["CRPYears"] = self._crp_years
        df_flat["TaxCreditCase"] = self._get_tax_credit_case()

        new_cols = [
            "Parameter",
            "Case",
            "TaxCreditCase",
            "CRPYears",
            "Technology",
            "DisplayName",
            "Scenario",
        ] + list(old_cols)
        df_flat = df_flat[new_cols]
        df_flat = df_flat.drop(TECH_DETAIL_SCENARIO_COL, axis=1).reset_index(drop=True)

        return df_flat

    def get_depreciation_schedule(self, year: int) -> List[float]:
        """
        Provide a function to return the depreciation schedule.  Not used for most techs, but some
        child classes vary by year based on Inflation Reduction Act credits

        @param year - integer of analysis year
        """
        return self._depreciation_schedule

    def get_meta_data(self) -> pd.DataFrame:
        """
        Get meta data/technology classification
        """
        return self._extractor.get_meta_data()

    def test_lcoe(self):
        """
        Test calculated LCOE against values in workbook. Raise exception
        if there is a discrepancy.
        """
        if not self.has_lcoe:
            print(f"LCOE is not calculated for {self.sheet_name}, skipping test.")
            return
        assert self.df_lcoe is not None, "Please run `run()` first to calculate LCOE."

        self.ss_lcoe = self._extractor.get_metric_values(
            LCOE_SS_NAME, self.num_tds, self.split_metrics
        )

        assert (
            not self.df_lcoe.isnull().any().any()
        ), f"Error in calculated LCOE, found missing values: {self.df_lcoe}"
        assert (
            not self.ss_lcoe.isnull().any().any()
        ), f"Error in LCOE from workbook, found missing values: {self.ss_lcoe}"

        if np.allclose(
            np.array(self.df_lcoe, dtype=float), np.array(self.ss_lcoe, dtype=float)
        ):
            print("Calculated LCOE matches LCOE from workbook")
        else:
            msg = f"Calculated LCOE doesn't match LCOE from workbook for {self.sheet_name}"
            print(msg)
            print("Workbook LCOE:")
            print(self.ss_lcoe)
            print("DF LCOE:")
            print(self.df_lcoe)
            raise ValueError(msg)

    def test_capex(self):
        """
        Test calculated CAPEX against values in workbook. Raise exception
        if there is a discrepancy.
        """
        if not self.has_capex:
            print(f"CAPEX is not calculated for {self.sheet_name}, skipping test.")
            return
        assert self.df_capex is not None, "Please run `run()` first to calculate CAPEX."

        self.ss_capex = self._extractor.get_metric_values(
            CAPEX_SS_NAME, self.num_tds, self.split_metrics
        )

        assert (
            not self.df_capex.isnull().any().any()
        ), f"Error in calculated CAPEX, found missing values: {self.df_capex}"
        assert (
            not self.ss_capex.isnull().any().any()
        ), f"Error in CAPEX from workbook, found missing values: {self.ss_capex}"
        if np.allclose(
            np.array(self.df_capex, dtype=float), np.array(self.ss_capex, dtype=float)
        ):
            print("Calculated CAPEX matches CAPEX from workbook")
        else:
            raise ValueError("Calculated CAPEX doesn't match CAPEX from workbook")

    def _flat_fin_assump(self):
        """
        Financial assumptions from WACC_Calc sheet by year for flat output: add
        FCR and reformat index.

        @returns {pd.DataFrame}
        """
        assert self.df_wacc is not None, (
            "df_wacc must not be None to flatten " "financial assumptions."
        )

        df = self.df_wacc.copy()

        # Add CRF and FCR
        if self.has_tax_credit and self.df_pff is not None:
            for scenario in self.scenarios:
                wacc = df.loc[f"WACC Real - {scenario}"]
                pff = self.df_pff.loc[f"PFF - {scenario}"]
                crf, fcr = self._calc_fcr(wacc, self._crp_years, pff, scenario)
                df = pd.concat([df, crf, fcr])
        else:
            # No tax credit, just fill with *
            cols = df.columns
            fcr = pd.DataFrame({c: ["*"] for c in cols}, index=["FCR"])
            crf = pd.DataFrame({c: ["*"] for c in cols}, index=["CRF"])
            df = pd.concat([df, crf, fcr])

        # Explode index and clean up
        df.index.rename("WACC", inplace=True)
        df = df.reset_index(drop=False)
        df[["Parameter", "Scenario"]] = df.WACC.str.split(" - ", expand=True)
        df.loc[df.Scenario.isnull(), "Scenario"] = "*"
        df.loc[df.Scenario == "Nominal", "Parameter"] = (
            "Interest During Construction - Nominal"
        )
        df.loc[df.Scenario == "Nominal", "Scenario"] = "*"
        df["DisplayName"] = "*"
        df["TaxCreditCase"] = self._get_tax_credit_case()

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
        crf = wacc / (1 - 1 / (1 + wacc) ** crp)
        fcr = crf * pff
        crf.name = f"CRF - {scenario}"
        fcr.name = f"FCR - {scenario}"
        crf = pd.DataFrame(crf).T
        fcr = pd.DataFrame(fcr).T

        return crf, fcr

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

    @classmethod
    def load_cff(
        cls, extractor: Extractor, cff_name: str, index: pd.Index, return_short_df=False
    ) -> pd.DataFrame:
        """
        Load CFF data from workbook and duplicate for all tech details. This method is
        a little weird due to testing needs.

        @param extractor - workbook extractor instance
        @param cff_name - name of CFF data in SS
        @param index - Index of a "normal" data frame for this tech to use for df_cff
        @param return_short_df - return original 3 row data frame if True
        @returns - CFF data frame
        """
        df_cff = extractor.get_cff(cff_name, len(cls.scenarios))
        assert len(df_cff) == len(cls.scenarios), (
            f"Wrong number of CFF rows found. Expected {len(cls.scenarios)}, "
            f"get {len(df_cff)}."
        )

        if return_short_df:
            return df_cff

        # CFF only has values for the three scenarios. Duplicate for all tech details
        full_df_cff = pd.DataFrame()
        for _ in range(cls.num_tds):
            full_df_cff = pd.concat([full_df_cff, df_cff])
        full_df_cff.index = index

        return full_df_cff

    def _calc_aep(self):
        assert self.df_ncf is not None, "NCF must to loaded to calculate AEP"
        df_aep = self.df_ncf * 8760
        return df_aep

    def _calc_capex(self):
        assert (
            self.df_cff is not None
            and self.df_occ is not None
            and self.df_gcc is not None
        ), "CFF, OCC, and GCC must to loaded to calculate CAPEX"
        df_capex = self.df_cff * (self.df_occ + self.df_gcc)
        df_capex = df_capex.copy()
        return df_capex

    def _calc_con_fin_cost(self):
        df_cfc = (self.df_cff - 1) * (self.df_occ + self.df_gcc)
        df_cfc = df_cfc.copy()
        return df_cfc

    def _calc_crf(self):
        df_crf = self.df_just_wacc / (1 - (1 / (1 + self.df_just_wacc)) ** self.crp)

        # Relabel WACC index as CRF
        df_crf = df_crf.reset_index()
        df_crf["WACC Type"] = df_crf["WACC Type"].apply(
            lambda x: "Capital Recovery Factor (CRF)" + x[4:]
        )
        df_crf = df_crf.loc[df_crf["WACC Type"].str.contains("Real")]
        df_crf = df_crf.set_index("WACC Type")

        return df_crf

    @property
    def crp(self) -> float:
        """
        Get CRP value from financial assumptions

        @returns: CRP
        """
        raw_crp = self.df_fin.loc["Capital Recovery Period (Years)", "Value"]

        try:
            crp = float(raw_crp)
        except ValueError as err:
            msg = f"Error converting CRP value ({raw_crp}) to a float: {err}."
            print(f"{msg} self.df_fin is:")
            print(self.df_fin)
            raise ValueError(msg) from err

        assert not np.isnan(
            crp
        ), f'CRP must be a number, got "{crp}", type is "{type(crp)}"'
        return crp

    def _calc_itc(self, itc_type=""):
        """
        Calculate ITC if used

        @param {str} itc_type - type of ITC to search for (used for utility PV + batt)
        @returns {np.ndarray|int} - array of ITC values or 0
        """
        if self.has_tax_credit:
            itc_index = f"ITC Schedule{itc_type}/*"
            assert itc_index in self.df_tc.index, (
                "ITC schedule not found in "
                f'tax credit data. Looking for "{itc_index}" in:\n{self.df_tc}'
            )
            df_itc_schedule = self.df_tc.loc[itc_index]
            itc_schedule = df_itc_schedule.values
        else:
            itc_schedule = 0

        return itc_schedule

    def _calc_pff(self, itc_type=""):
        """
        Calculate PFF

        @param {str} itc_type - type of ITC to search for (used for utility PV + batt)
        @returns {pd.DataFrame} - dataframe of PFF
        """
        df_tax_rate = self.df_wacc.loc["Tax Rate (Federal and State)"]
        inflation = self.df_wacc.loc["Inflation Rate"]

        df_pvd = pd.DataFrame(columns=self._tech_years)
        for scenario in self.scenarios:
            for year in self._tech_years:

                MACRS_schedule = self.get_depreciation_schedule(year)

                df_depreciation_factor = self._calc_dep_factor(
                    MACRS_schedule, inflation, scenario
                )

                df_pvd.loc["PVD - " + scenario, year] = np.dot(
                    MACRS_schedule, df_depreciation_factor[year]
                )

        itc_schedule = self._calc_itc(itc_type=itc_type)

        df_pff = (
            1 - df_tax_rate.values * df_pvd * (1 - itc_schedule / 2) - itc_schedule
        ) / (1 - df_tax_rate.values)
        df_pff.index = [f"PFF - {scenario}" for scenario in self.scenarios]
        return df_pff

    def _calc_dep_factor(self, MACRS_schedule, inflation, scenario):
        """
        Calculate the depreciation factor

        @param {list of float} MACRS_schedule - MACRS
        @param {pd.Series} inflation - inflation by year
        @param {string} scenario - tech scenario

        @returns {pd.DataFrame} - Depreciation factor. Columns are atb years, rows are
            depreciation years.
        """
        dep_years = len(MACRS_schedule)
        df_depreciation_factor = pd.DataFrame(columns=self._tech_years)
        wacc_real = self.df_wacc.loc["WACC Real - " + scenario]

        for dep_year in range(dep_years):
            df_depreciation_factor.loc[dep_year + 1] = 1 / (
                (1 + wacc_real) * (1 + inflation)
            ) ** (dep_year + 1)

        return df_depreciation_factor

    def _calc_ptc(self):
        """
        Calculate PTC if used

        @returns {np.ndarray|int} - array of PTC values or 0
        """
        if self.has_tax_credit:
            df_tax_credit = self.df_tc.reset_index()
            df_ptc = df_tax_credit.loc[
                df_tax_credit["Tax Credit"].str.contains("PTC/", na=False)
            ]

            assert len(df_ptc) != 0, f"PTC data is missing for {self.sheet_name}"
            assert len(df_ptc) == len(
                self.scenarios
            ), f"Wrong amount of PTC data for{self.sheet_name}"

            df_ptc = pd.concat([df_ptc] * self.num_tds).set_index("Tax Credit")
            ptc = df_ptc.values
        else:
            ptc = 0

        return ptc

    def _calc_lcoe(self):
        ptc = self._calc_ptc()

        assert len(self.df_crf) == len(self.scenarios), (
            f"CRF has {len(self.df_crf)} rows ({self.df_crf.index}), but there "
            f"are {len(self.scenarios)} scenarios ({self.scenarios})"
        )

        x = self.df_crf.values * self.df_pff
        y = pd.concat([x] * self.num_tds)

        df_lcoe = (
            1000 * (y.values * self.df_capex.values + self.df_fom) / self.df_aep.values
        )
        df_lcoe = df_lcoe + self.df_vom.values - ptc

        return df_lcoe

    def _get_tax_credit_case(self):
        """
        Uses ptc and itc data from the tech sheet to determine which tax credits are active for the
        current financial case and tax credit case

        @returns String, one of "None", "PTC", "ITC", "ITC + PTC"
        """
        if not self.has_tax_credit:
            return "None"
        assert (
            len(self.df_tc) > 0
        ), f"Setup df_tc with extractor.get_tax_credits() before calling this function!"

        ptc = self._calc_ptc()
        itc = self._calc_itc()

        # Trim the 2022 to eliminate pre-inflation reduction act confusion (consider removing in future years)
        ptc = ptc[:, 1:]
        itc = itc[1:]

        ptc_sum = np.sum(ptc)
        itc_sum = np.sum(itc)

        if ptc_sum > 0 and itc_sum > 0:
            return "PTC + ITC"
        if ptc_sum > 0:
            return "PTC"
        if itc_sum > 0:
            return "ITC"
        else:
            return "None"
