"""
Test that the LCOE and CAPEX processing code works properly.
"""
import numpy as np
import pandas as pd

from lcoe_calculator.base_processor import CRP_CHOICES
from lcoe_calculator.tech_processors import ALL_TECHS, TechProcessor
from lcoe_calculator.config import FINANCIAL_CASES

from .mock_extractor import MockExtractor
from .data_finder import DataFinder

def test_lcoe_and_capex_calculations():
    """
    Test LCOE and CAPEX calculations using stored data
    """
    for tech in ALL_TECHS:
        print(f'----------- Testing {tech.sheet_name} -----------')
        for case in FINANCIAL_CASES:
            for crp in CRP_CHOICES:
                DataFinder.set_tech(tech)

                proc: TechProcessor = tech('fake_path_to_data_master.xlsx', case=case, crp=crp,
                                           extractor=MockExtractor)
                proc.run()

                # Check all metrics have been loaded
                for metric in proc.metrics:
                    df = getattr(proc, metric[1])
                    assert isinstance(df, pd.DataFrame)
                    assert not df.isnull().any().any()

                # Check all data for export has been loaded or calculated
                for flat_attr in proc.flat_attrs:
                    df = getattr(proc, flat_attr[0])
                    assert isinstance(df, pd.DataFrame)
                    assert not df.isnull().any().any()

                # Compare python calculated CAPEX and LCOE to values originally calculated in the
                # spreadsheet.
                if proc.has_capex:
                    proc.test_capex()
                    assert not proc.df_capex.isnull().any().any()
                    assert not proc.ss_capex.isnull().any().any()
                    assert np.allclose(np.array(proc.df_capex, dtype=float),
                                    np.array(proc.ss_capex, dtype=float))
                if proc.has_lcoe:
                    proc.test_lcoe()
                    assert not proc.df_lcoe.isnull().any().any()
                    assert not proc.ss_lcoe.isnull().any().any()
                    assert np.allclose(np.array(proc.df_lcoe, dtype=float),
                                    np.array(proc.ss_lcoe, dtype=float))

if __name__ == '__main__':
    test_lcoe_and_capex_calculations()
