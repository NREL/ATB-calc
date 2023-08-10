# Debt Fraction Calculator
This code utilizes the processing code of the `lcoe_calculator` module with the [PySAM](https://nrel-pysam.readthedocs.io/en/main/)
package to compute new debt fractions given the cost and tax credit assumptions in the ATB data workbook `xlsx` document.

For more on the financial assumptions used for these calculations see the [ATB documentation](https://atb.nrel.gov/electricity/2023/financial_cases_&_methods)
and the [SAM documentation](https://sam.nrel.gov/financial-models/utility-scale-ppa.html).

To run:
- Open the data workbook Excel file and make your desired adjustments to the data
- From the root repository folder run `python -m debt_fraction_calculator.debt_fraction_calc` as
described in the main repository README
- Copy values to the WACC Calc tab of the data workbook as appropriate