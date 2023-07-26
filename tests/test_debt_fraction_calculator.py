from debt_fraction_calculator.debt_fraction_calc import calculate_debt_fraction
from lcoe_calculator.macrs import MACRS_6, MACRS_16, MACRS_21

import pytest

"""
        CF - capacity factor (%, 0-1)
        OCC - overnight capital cost ($/kW)
        CFC - construction financing cost ($/kW)
        Fixed O&M - fixed operations and maintenance ($/kW-yr)
        Variable O&M - variable operations and maintenance ($/Mwh)
        DSCR - Debt service coverage ratio (unitless, typically 1-1.5)
        IRR - internal rate of return (%, 0-1)
        Tax Rate (Federal and State) (%, 0-1)
        Inflation Rate (%, 0-1)
        Fuel - Fuel cost ($/MMBtu) - optional
        Heat Rate - (MMBtu/MWh) - optional
        Interest Rate Nominal (%, 0-1)
        Calculated Rate of Return on Equity Real (%, 0-1)
        ITC - Investment tax Credit, federal (%, 0-1)
        PTC - Production tax credit, federal ($/MWh)
"""

def test_no_tax_credits():
    # 2023 ATB utility PV, 2030, R&D case
    input_vals = {
        "CF" : 0.29485,
        "OCC" : 1043.0,
        "CFC" : 38.0,
        "Fixed O&M" : 18.0,
        "Variable O&M" : 0.0,
        "DSCR" : 1.3,
        "Rate of Return on Equity Nominal" : 0.088,
        "Tax Rate (Federal and State)" : 0.257,
        "Inflation Rate" : 0.025,
        "Interest Rate Nominal" : 0.07,
        "Calculated Rate of Return on Equity Real" : 0.061,
        "ITC" : 0,
        "PTC" : 0,
        "MACRS" : MACRS_6
    }

    debt_frac = calculate_debt_fraction(input_vals)

    assert debt_frac == pytest.approx(73.8, 0.1)

def test_ptc():
    # 2023 ATB utility PV, 2030, Markets case
    input_vals = {
        "CF" : 0.29485,
        "OCC" : 1043.0,
        "CFC" : 38.0,
        "Fixed O&M" : 18.0,
        "Variable O&M" : 0.0,
        "DSCR" : 1.3,
        "Rate of Return on Equity Nominal" : 0.088,
        "Tax Rate (Federal and State)" : 0.257,
        "Inflation Rate" : 0.025,
        "Interest Rate Nominal" : 0.07,
        "Calculated Rate of Return on Equity Real" : 0.061,
        "ITC" : 0,
        "PTC" : 25.46,
        "MACRS" : MACRS_6
    }

    debt_frac = calculate_debt_fraction(input_vals)

    assert debt_frac == pytest.approx(45.5, 0.1)

def test_itc():
    # 2023 ATB utility PV, 2030, Markets case
    input_vals = {
        "CF" : 0.29485,
        "OCC" : 1043.0,
        "CFC" : 38.0,
        "Fixed O&M" : 18.0,
        "Variable O&M" : 0.0,
        "DSCR" : 1.3,
        "Rate of Return on Equity Nominal" : 0.088,
        "Tax Rate (Federal and State)" : 0.257,
        "Inflation Rate" : 0.025,
        "Interest Rate Nominal" : 0.07,
        "Calculated Rate of Return on Equity Real" : 0.061,
        "ITC" : 0.3,
        "PTC" : 0,
        "MACRS" : MACRS_6
    }

    debt_frac = calculate_debt_fraction(input_vals)

    assert debt_frac == pytest.approx(51.8, 0.1)

def test_heat_rate():
    # Nuclear, 2030
    input_vals = {
        "CF" : 0.93,
        "OCC" : 6115.0,
        "CFC" : 1615.0,
        "Fixed O&M" : 152.0,
        "Variable O&M" : 2.0,
        "DSCR" : 1.45,
        "Rate of Return on Equity Nominal" : 0.11,
        "Tax Rate (Federal and State)" : 0.257,
        "Inflation Rate" : 0.025,
        "Interest Rate Nominal" : 0.08,
        "Calculated Rate of Return on Equity Real" : 0.083,
        "ITC" : 0.3,
        "PTC" : 0,
        "MACRS" : MACRS_6,
        "Fuel" : 7.0,
        "Heat Rate" : 10.45
    }

    debt_frac = calculate_debt_fraction(input_vals)

    assert debt_frac == pytest.approx(48.9, 0.1)