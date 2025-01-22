#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Find path to test data CSV files. General layout:

    ./data/{tech}/df_ncf.csv
    ./data/{tech}/{case}/df_cff.csv
    ./data/{tech}/{case}/{crp}/df_fin_assump.csv
    ./data/{tech}/{case}/{crp}/df_lcoe.csv
    ./data/{tech}/{case}/{crp}/df_capex.csv
    ./data/{tech}/{case}/{crp}/df_occ.csv
    ./data/{tech}/{case}/{crp}/etc
"""
from typing import Optional, Type
import os
from lcoe_calculator.base_processor import TechProcessor
from lcoe_calculator.config import LCOE_SS_NAME, CAPEX_SS_NAME, CrpChoiceType

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# These metrics do not have real headers in the data workbook. Create fake ones so data can be
# stored for testing purposes.
FIN_ASSUMP_FAKE_SS_NAME = "financial assumptions"
WACC_FAKE_SS_NAME = "wacc"
JUST_WACC_FAKE_SS_NAME = "just wacc"
TAX_CREDIT_FAKE_SS_NAME = "tax credit"


class DataFinder:
    """
    Get path and file names for saving tech metric values to CSV. Note that set_tech() must
    be used before first use and before being used for a new tech.
    """

    _tech: Optional[Type[TechProcessor]] = None

    @classmethod
    def set_tech(cls, tech: Type[TechProcessor]):
        """
        Set the tech currently being processed. This must be run before using get_data_filename().

        @param tech - The tech processor paths and files name are being found for.
        """
        cls._tech = tech

    @classmethod
    def get_data_filename(cls, metric: str, case: str, crp: CrpChoiceType):
        """
        Get path and filename to test data.

        @param metric - long name of desired metric, e.g.: 'CAPEX ($/kW)'
        @param case - name of desired financial case
        @param crp - name of desired CRP
        @returns path to CSV file for metric in testing data dir
        """
        assert (
            cls._tech is not None
        ), "The TechProcessor must be set first with set_tech()."

        # Create a lookup table between fancy long names in the workbook and names to use for the
        # data files. This table partially borrows from the metrics list.
        metric_lookup = list(cls._tech.metrics)
        metric_lookup += [
            (LCOE_SS_NAME, "df_lcoe"),
            (CAPEX_SS_NAME, "df_capex"),
            (FIN_ASSUMP_FAKE_SS_NAME, "df_fin_assump"),
            (WACC_FAKE_SS_NAME, "df_wacc"),
            (JUST_WACC_FAKE_SS_NAME, "df_just_wacc"),
            (TAX_CREDIT_FAKE_SS_NAME, "df_tc"),
        ]
        assert metric in [
            m[0] for m in metric_lookup
        ], f"metric {metric} is not known for sheet {cls._tech.sheet_name}"
        df_name = [m[1] for m in metric_lookup if m[0] == metric][0]

        # Files in ./data/{tech}
        clean_sheet_name = str(cls._tech.sheet_name).replace(" ", "_")
        tech_dir = os.path.join(DATA_DIR, clean_sheet_name)
        if not os.path.exists(tech_dir):
            os.makedirs(tech_dir)
        if df_name in ["df_ncf"]:
            return os.path.join(tech_dir, f"{df_name}.csv")

        # Files in ./data/{tech}/{case}
        case_dir = os.path.join(tech_dir, case)
        if not os.path.exists(case_dir):
            os.makedirs(case_dir)
        if df_name in ["df_cff", "df_wacc", "df_just_wacc"]:
            return os.path.join(case_dir, f"{df_name}.csv")

        # Files in ./data/{tech}/{case}/{crp}
        crp_dir = os.path.join(case_dir, str(crp))
        if not os.path.exists(crp_dir):
            os.makedirs(crp_dir)
        return os.path.join(crp_dir, f"{df_name}.csv")
