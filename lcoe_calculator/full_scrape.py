"""
Scrape ATB data master and calculate all metrics.
"""
from typing import List, Dict, Type
from datetime import datetime as dt
import click
import pandas as pd

from .tech_processors import ALL_TECHS
from .base_processor import CRP_CHOICES, TechProcessor
from .config import FINANCIAL_CASES

class FullScrape:
    """
    Scrape datamaster and calculate LCOE for techs, CRPs, and financial
    scenarios.
    """
    def __init__(self, data_master_fname: str,
                 techs: List[TechProcessor]|TechProcessor|None = None):
        """
        @param data_master_fname - name of spreadsheet
        @param techs - one or more techs to run, all if None
        """
        if techs is None:
            techs = ALL_TECHS

        if not isinstance(techs, list):
            techs = [techs]

        self.data = None  # Flat data from scrape
        self.meta = None  # Meta data from scrape

        self._techs = techs
        self._fname = data_master_fname

    def scrape(self, test_capex: bool = True, test_lcoe: bool = True):
        """ Scrap all techs """
        self.data = pd.DataFrame()  # Flat data from scrape
        self.meta = pd.DataFrame()  # Meta data from scrape

        for i, tech in enumerate(self._techs):
            print(f'##### Processing {tech.tech_name} ({i+1}/{len(self._techs)}) #####')

            for crp in CRP_CHOICES:
                # skip TechLife if 20 or 30 so we don't dupliacte effort
                if crp == 'TechLife' and str(tech.tech_life) in CRP_CHOICES:
                    continue

                for case in FINANCIAL_CASES:
                    proc = tech(self._fname, crp=crp, case=case)
                    proc.run()

                    if test_capex:
                        proc.test_capex()
                    if test_lcoe:
                        proc.test_lcoe()

                    flat = proc.flat
                    self.data = pd.concat([self.data, flat])

            meta = proc.get_meta_data()
            meta['Tech Name'] = tech.tech_name
            self.meta = pd.concat([self.meta, meta])

        self.data = self.data.reset_index(drop=True)
        self.meta = self.meta.reset_index(drop=True)

    @property
    def data_flattened(self):
        """ Get flat data pivoted with each year as a row """
        if self.data is None:
            raise ValueError('Please run scrape() first')

        melted = pd.melt(self.data, id_vars=['Parameter', 'Case', 'CRPYears',
                                             'Technology', 'DisplayName', 'Scenario'])
        return melted

    def to_csv(self, fname: str):
        """ Write data to CSV """
        if self.data is None:
            raise ValueError('Please run scrape() first')

        self.data.to_csv(fname)

    def flat_to_csv(self, fname: str):
        """ Write pivoted data to CSV """
        if self.data is None:
            raise ValueError('Please run scrape() first')
        self.data_flattened.to_csv(fname)

    def meta_data_to_csv(self, fname: str):
        """ Write meta data to CSV """
        if self.data is None:
            raise ValueError('Please run scrape() first')

        self.meta.to_csv(fname)


tech_names = [tech.__name__ for tech in ALL_TECHS]

@click.command
@click.argument('data_master_filename', type=click.Path(exists=True))
@click.option('-t', '--tech', type=click.Choice(tech_names),
              help="Name of tech to scrape. Scrape all techs if none are specified.")
@click.option('-m', '--save-meta', 'meta_file', type=click.Path(),
              help="Save meta data to CSV.")
@click.option('-f', '--save-flat', 'flat_file', type=click.Path(),
              help="Save data in flat format to CSV.")
@click.option('-p', '--save-pivoted', 'pivoted_file', type=click.Path(),
              help="Save data in pivoted format to CSV.")
@click.option('-c', '--clipboard', is_flag=True, default=False,
              help="Copy data to system clipboard.")
def run_scrape(data_master_filename: str, tech: str|None, meta_file: str|None, flat_file: str|None,
               pivoted_file: str|None, clipboard: bool):
    """
    CLI to scrape ATB data master spreadsheet and calculate metrics.
    """
    tech_map: Dict[str, Type[TechProcessor]] = {tech.__name__: tech for tech in ALL_TECHS}

    if tech is not None:
        tech = tech_map[tech]

    start_dt = dt.now()
    scraper = FullScrape(data_master_filename, tech)
    scraper.scrape()
    click.echo(f'Scrape completed in {dt.now()-start_dt}.')

    if meta_file:
        click.echo(f'Writing meta data to {meta_file}.')
        scraper.meta_data_to_csv(meta_file)

    if flat_file:
        click.echo(f'Writing flat data to {flat_file}.')
        scraper.flat_to_csv(flat_file)

    if pivoted_file:
        click.echo(f'Writing pivoted data to {pivoted_file}.')
        scraper.to_csv(pivoted_file)

    if clipboard:
        click.echo('Data was copied to clipboard.')
        scraper.data.to_clipboard()


if __name__ == '__main__':
    run_scrape()
