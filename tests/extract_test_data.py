#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Extract values from the data workbook and save to the tests data directory.
"""
from typing import Dict, Type
import click

from lcoe_calculator.base_processor import TechProcessor
from lcoe_calculator.tech_processors import ALL_TECHS
from lcoe_calculator.extractor import Extractor
from lcoe_calculator.config import (
    FINANCIAL_CASES,
    LCOE_SS_NAME,
    CAPEX_SS_NAME,
    CFF_SS_NAME,
    CRP_CHOICES,
    CrpChoiceType,
)
from .data_finder import (
    DataFinder,
    FIN_ASSUMP_FAKE_SS_NAME,
    WACC_FAKE_SS_NAME,
    JUST_WACC_FAKE_SS_NAME,
    TAX_CREDIT_FAKE_SS_NAME,
)


# Use extractor to pull values from data workbook and save as CSV
def extract_data_for_crp_case(
    data_workbook_fname: str, tech: Type[TechProcessor], case: str, crp: CrpChoiceType
):
    """
    Extract data from ATB data workbook for a tech and save as CSV.

    @param data_workbook_fname - file name and path to ATB data workbook
    @param tech - tech processor class to extract data for
    @param case - name of desired financial case
    @param crp - name of desired CRP
    """
    extractor = Extractor(
        data_workbook_fname,
        str(tech.sheet_name),
        case,
        crp,
        tech.scenarios,
        base_year=tech.base_year,
    )

    metrics = list(tech.metrics)

    if tech.has_lcoe:
        metrics.append((LCOE_SS_NAME, ""))

    if tech.has_capex:
        metrics.append((CAPEX_SS_NAME, ""))

    extract_cff = False
    for metric, _ in metrics:
        if metric == CFF_SS_NAME:
            extract_cff = True
            continue

        df = extractor.get_metric_values(metric, tech.num_tds, tech.split_metrics)
        index = df.index
        fname = DataFinder.get_data_filename(metric, case, crp)
        df.to_csv(fname)

    if extract_cff:
        df_cff = tech.load_cff(extractor, CFF_SS_NAME, index, return_short_df=True)
        fname = DataFinder.get_data_filename(CFF_SS_NAME, case, crp)
        df_cff.to_csv(fname)

    if tech.has_fin_assump:
        df_fin = extractor.get_fin_assump()
        fname = DataFinder.get_data_filename(FIN_ASSUMP_FAKE_SS_NAME, case, crp)
        df_fin.to_csv(fname)

    if tech.has_wacc:
        (df_wacc, df_just_wacc) = extractor.get_wacc(tech.wacc_name)
        fname = DataFinder.get_data_filename(WACC_FAKE_SS_NAME, case, crp)
        df_wacc.to_csv(fname)
        fname = DataFinder.get_data_filename(JUST_WACC_FAKE_SS_NAME, case, crp)
        df_just_wacc.to_csv(fname)

    if tech.has_tax_credit:
        df_tc = extractor.get_tax_credits()
        fname = DataFinder.get_data_filename(TAX_CREDIT_FAKE_SS_NAME, case, crp)
        df_tc.to_csv(fname)


tech_names = [tech.__name__ for tech in ALL_TECHS]


@click.command
@click.argument("filename", type=click.Path(exists=True))
@click.option("-t", "--tech", type=click.Choice(tech_names))
def extract(filename: str, tech: str | None):
    """
    Extract test data for one or more techs for all CRPs and financial cases. Data will be extracted
    from the Excel ATB data workbook FILENAME and saved as CSV for testing.
    """
    tech_map: Dict[str, Type[TechProcessor]] = {
        tech.__name__: tech for tech in ALL_TECHS
    }

    if tech is None:
        techs = ALL_TECHS
    else:
        techs = [tech_map[tech]]

    for Tech in techs:
        print(f"Extracting values for {Tech.sheet_name}")
        DataFinder.set_tech(Tech)

        for case in FINANCIAL_CASES:
            for crp in CRP_CHOICES:
                print(f"\tcrp={crp}, case={case}")
                extract_data_for_crp_case(filename, Tech, case, crp)

    print("Done")


if __name__ == "__main__":
    extract()  # pylint: disable=no-value-for-parameter
