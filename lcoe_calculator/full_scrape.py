import pandas as pd
from typing import List, Union

from tech_processors import OffShoreWindProc, LandBasedWindProc, DistributedWindProc,\
    UtilityPvProc, CommPvProc, ResPvProc, UtilityPvPlusBatteryProc,\
    CspProc, GeothermalProc, HydropowerProc, PumpedStorageHydroProc,\
    CoalProc, NaturalGasProc, NuclearProc, BiopowerProc,\
    UtilityBatteryProc, CommBatteryProc, ResBatteryProc,\
    CoalRetrofitProc, NaturalGasRetrofitProc
from base_processor import CRP_CHOICES
from extractor import FIN_CASES

class FullScrape:
    """
    Scrape datamaster and calculate LCOE for all techs, CRPs, and financial
    scenarios.
    """
    def __init__(self, data_master_fname: str, techs: Union[List, None] = None):
        """
        @param {str} data_master_fname - name of spreadsheet
        @param {list|None} techs - techs to run, all if None
        """
        if techs is None:
            techs = [
                OffShoreWindProc, LandBasedWindProc, DistributedWindProc,
                UtilityPvProc, CommPvProc, ResPvProc, UtilityPvPlusBatteryProc,
                CspProc, GeothermalProc, HydropowerProc, PumpedStorageHydroProc,
                CoalProc, NaturalGasProc, NuclearProc, BiopowerProc,
                UtilityBatteryProc, CommBatteryProc, ResBatteryProc,
                CoalRetrofitProc, NaturalGasRetrofitProc
            ]

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
                # skip TechLife if 20 or 30
                if crp == 'TechLife' and str(tech.tech_life) in CRP_CHOICES:
                    continue

                for case in FIN_CASES:
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
