"""
Extract values from the data master and save to the tests data directory.
"""
from typing import Dict, Type
import click

from lcoe_calculator.base_processor import TechProcessor, CRP_CHOICES, LCOE, CAPEX,\
    CONSTRUCTION_FINANCE_FACTOR
from lcoe_calculator.tech_processors import ALL_TECHS
from lcoe_calculator.extractor import Extractor, FIN_CASES
from .data_finder import DataFinder, FINANCIAL_ASSUMPTIONS, WACC, JUST_WACC, TAX_CREDIT

# Use extractor to pull values from data master and save as CSV
def extract_data_for_crp_case(data_master_fname: str, tech: TechProcessor, case: str, crp: str|int):
    """
    Extract data from ATB data master spreadsheet for a tech and save as CSV.

    @param data_master_fname - file name and path to ATB data master
    @param tech - tech processor class to extract data for
    @param case - name of desired financial case
    @param crp - name of desired CRP
    """
    extractor = Extractor(data_master_fname, tech.sheet_name, case, crp,
                          tech.scenarios, base_year=tech.base_year)

    metrics = list(tech.metrics)

    if tech.has_lcoe:
        metrics.append((LCOE, ''))

    if tech.has_capex:
        metrics.append((CAPEX, ''))

    extract_cff = False
    for metric, _ in metrics :
        if metric == CONSTRUCTION_FINANCE_FACTOR:
            extract_cff = True
            continue

        df = extractor.get_metric_values(metric, tech.num_tds, tech.split_metrics)
        index = df.index
        fname = DataFinder.get_data_filename(metric, case, crp)
        df.to_csv(fname)

    if extract_cff:
        df_cff = tech.load_cff(extractor, CONSTRUCTION_FINANCE_FACTOR, index, return_short_df=True)
        fname = DataFinder.get_data_filename(CONSTRUCTION_FINANCE_FACTOR,
                                  case, crp)
        df_cff.to_csv(fname)

    if tech.has_fin_assump:
        df_fin = extractor.get_fin_assump()
        fname = DataFinder.get_data_filename(FINANCIAL_ASSUMPTIONS, case, crp)
        df_fin.to_csv(fname)

    if tech.has_wacc:
        (df_wacc, df_just_wacc) = extractor.get_wacc(tech.wacc_name)
        fname = DataFinder.get_data_filename(WACC, case, crp)
        df_wacc.to_csv(fname)
        fname = DataFinder.get_data_filename(JUST_WACC, case, crp)
        df_just_wacc.to_csv(fname)

    if tech.has_tax_credit:
        df_tc = extractor.get_tax_credits()
        fname = DataFinder.get_data_filename(TAX_CREDIT, case, crp)
        df_tc.to_csv(fname)


tech_names = [tech.__name__ for tech in ALL_TECHS]

@click.command
@click.argument('filename', type=click.Path(exists=True))
@click.option('-t', '--tech', type=click.Choice(tech_names))
def extract(filename: str, tech: str|None):
    """
    Extract test data for one or more techs for all CRPs and financial cases. Data will be extracted
    from the data master spreadsheet FILENAME and saved as CSV for testing.
    """
    tech_map: Dict[str, Type[TechProcessor]] = {tech.__name__: tech for tech in ALL_TECHS}

    if tech is None:
        techs = ALL_TECHS
    else:
        techs = [tech_map[tech]]

    for tech in techs:
        print(f'Extracting values for {tech.sheet_name}')
        DataFinder.set_tech(tech)

        for case in FIN_CASES:
            for crp in CRP_CHOICES:
                print(f'\tcrp={crp}, case={case}')
                extract_data_for_crp_case(filename, tech, case, crp)

    print('Done')


if __name__ == '__main__':
    extract()
