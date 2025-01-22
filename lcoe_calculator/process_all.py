#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Process all (or some) ATB technologies and calculate all metrics.
"""
from typing import List, Dict, Type
from datetime import datetime as dt
import click
import pandas as pd

from .tech_processors import ALL_TECHS
from .base_processor import TechProcessor
from .config import (
    FINANCIAL_CASES,
    MARKET_FIN_CASE,
    CRP_CHOICES,
    CrpChoiceType,
    TAX_CREDIT_CASES,
)


class ProcessAll:
    """
    Extract data from ATB workbook and calculate LCOE for techs, CRPs, and financial
    scenarios.
    """

    def __init__(
        self,
        data_workbook_fname: str,
        techs: List[Type[TechProcessor]] | Type[TechProcessor],
    ):
        """
        @param data_workbook_fname - name of workbook
        @param techs - one or more techs to run
        """
        if not isinstance(techs, list):
            techs = [techs]

        self.data = pd.DataFrame()  # Flat data
        self.meta = pd.DataFrame()  # Meta data

        self._techs = techs
        self._fname = data_workbook_fname

    def _run_tech(
        self,
        Tech: TechProcessor,
        crp: CrpChoiceType,
        case: str,
        tcc: str,
        test_capex,
        test_lcoe,
    ):
        """
        Runs the specified Tech with the specified parameters
        @param Tech - TechProcessor to be processed
        @param crp - cost recovery period, one of CrpChoiceType
        @param case - financial case
        @param tcc - tax credit case
        @param test_capex - boolean. True runs a comparison of the CAPEX to the spreadsheet
        @param test_lcoe - boolean. True runs a comparison of the LCOE to the spreadsheet

        @returns TechProcessor with processed data from the other inputs
        """
        proc = Tech(self._fname, crp=crp, case=case, tcc=tcc)
        proc.run()

        if test_capex:
            proc.test_capex()
        if test_lcoe:
            proc.test_lcoe()

        flat = proc.flat
        self.data = pd.concat([self.data, flat])

        return proc

    def process(self, test_capex: bool = True, test_lcoe: bool = True):
        """Process all techs"""
        self.data = pd.DataFrame()
        self.meta = pd.DataFrame()

        for i, Tech in enumerate(self._techs):
            print(f"##### Processing {Tech.tech_name} ({i+1}/{len(self._techs)}) #####")

            proc = None
            for crp in CRP_CHOICES:
                # skip TechLife if 20 or 30 so we don't duplicate effort
                if crp == "TechLife" and Tech.tech_life in CRP_CHOICES:
                    continue

                for case in FINANCIAL_CASES:
                    if case is MARKET_FIN_CASE and Tech.tech_name in TAX_CREDIT_CASES:
                        tax_cases = TAX_CREDIT_CASES[Tech.tech_name]
                        for tc in tax_cases:
                            proc = self._run_tech(
                                Tech, crp, case, tc, test_capex, test_lcoe
                            )
                    else:
                        proc = self._run_tech(
                            Tech, crp, case, None, test_capex, test_lcoe
                        )

            meta = proc.get_meta_data()
            meta["Tech Name"] = Tech.tech_name
            self.meta = pd.concat([self.meta, meta])

        self.data = self.data.reset_index(drop=True)
        self.meta = self.meta.reset_index(drop=True)

    @property
    def data_flattened(self):
        """Get flat data pivoted with each year as a row"""
        if self.data is None:
            raise ValueError("Please run process() first")

        melted = pd.melt(
            self.data,
            id_vars=[
                "Parameter",
                "Case",
                "TaxCreditCase",
                "CRPYears",
                "Technology",
                "DisplayName",
                "Scenario",
            ],
        )
        return melted

    def to_csv(self, fname: str):
        """Write data to CSV"""
        if self.data is None:
            raise ValueError("Please run process() first")

        self.data.to_csv(fname)

    def flat_to_csv(self, fname: str):
        """Write pivoted data to CSV"""
        if self.data is None:
            raise ValueError("Please run process() first")
        self.data_flattened.to_csv(fname)

    def meta_data_to_csv(self, fname: str):
        """Write meta data to CSV"""
        if self.data is None:
            raise ValueError("Please run process() first")

        self.meta.to_csv(fname)


tech_names = [Tech.__name__ for Tech in ALL_TECHS]


@click.command
@click.argument("data_workbook_filename", type=click.Path(exists=True))
@click.option(
    "-t",
    "--tech",
    type=click.Choice(tech_names),
    help="Name of tech to process. Process all techs if none are specified.",
)
@click.option(
    "-m", "--save-meta", "meta_file", type=click.Path(), help="Save meta data to CSV."
)
@click.option(
    "-f",
    "--save-flat",
    "flat_file",
    type=click.Path(),
    help="Save data in flat format to CSV.",
)
@click.option(
    "-p",
    "--save-pivoted",
    "pivoted_file",
    type=click.Path(),
    help="Save data in pivoted format to CSV.",
)
@click.option(
    "-c",
    "--clipboard",
    is_flag=True,
    default=False,
    help="Copy data to system clipboard.",
)
def process(
    data_workbook_filename: str,
    tech: str | None,
    meta_file: str | None,
    flat_file: str | None,
    pivoted_file: str | None,
    clipboard: bool,
):
    """
    CLI to process ATB data workbook and calculate metrics.
    """
    tech_map: Dict[str, Type[TechProcessor]] = {
        tech.__name__: tech for tech in ALL_TECHS
    }

    techs = ALL_TECHS if tech is None else [tech_map[tech]]

    start_dt = dt.now()
    processor = ProcessAll(data_workbook_filename, techs)
    processor.process()
    click.echo(f"Processing completed in {dt.now()-start_dt}.")

    if meta_file:
        click.echo(f"Writing meta data to {meta_file}.")
        processor.meta_data_to_csv(meta_file)

    if flat_file:
        click.echo(f"Writing flat data to {flat_file}.")
        processor.flat_to_csv(flat_file)

    if pivoted_file:
        click.echo(f"Writing pivoted data to {pivoted_file}.")
        processor.to_csv(pivoted_file)

    if clipboard:
        click.echo("Data was copied to clipboard.")
        processor.data.to_clipboard()


if __name__ == "__main__":
    process()  # pylint: disable=no-value-for-parameter
