#
# Copyright (c) Alliance for Sustainable Energy, LLC and Skye Analytics, Inc. See also https://github.com/NREL/ATB-calc/blob/main/LICENSE
#
# This file is part of ATB-calc
# (see https://github.com/NREL/ATB-calc).
#
"""
Workflow to calculate debt fractions based on ATB data

Developed against PySAM 4.0.0
"""
from typing import TypedDict, List, Dict, Type
import pandas as pd
import click

import PySAM.Levpartflip as levpartflip

from lcoe_calculator.extractor import Extractor
from lcoe_calculator.config import (
    YEARS,
    END_YEAR,
    FINANCIAL_CASES,
    CrpChoiceType,
    PTC_PLUS_ITC_CASE_PVB,
)
from lcoe_calculator.tech_processors import LCOE_TECHS
import lcoe_calculator.tech_processors
from lcoe_calculator.base_processor import TechProcessor
from lcoe_calculator.macrs import MACRS_6, MACRS_16, MACRS_21


InputVals = TypedDict(
    "InputVals",
    {
        "CF": float,  # Capacity factor (%, 0-1)
        "OCC": float,  # Overnight capital cost ($/kW)
        "CFC": float,  # Construction financing cost ($/kW)
        "Fixed O&M": float,  # Fixed operations and maintenance ($/kW-yr)
        "Variable O&M": float,  # Variable operations and maintenance ($/Mwh)
        "DSCR": float,  # Debt service coverage ratio (unitless, typically 1-1.5)
        "Rate of Return on Equity Nominal": float,  # Internal rate of return (%, 0-1)
        "Tax Rate (Federal and State)": float,  # (%, 0-1)
        "Inflation Rate": float,  # (%, 0-1)
        "Fuel": float,  # Fuel cost ($/MMBtu) - optional
        "Heat Rate": float,  # (MMBtu/MWh) - optional
        "Interest Rate Nominal": float,  # (%, 0-1)
        "Calculated Rate of Return on Equity Real": float,  # (%, 0-1)
        "ITC": float,  # Investment tax Credit, federal (%, 0-1)
        "PTC": float,  # Production tax credit, federal ($/MWh)
        "MACRS": List[float],  # Depreciation schedule from lcoe_calculator.macrs
    },
    total=False,
)


def calculate_debt_fraction(input_vals: InputVals, debug=False) -> float:
    """
    Calculate debt fraction using a single PySAM run.

    @param input_vals - Input values for PySAM
    @param debug - Print PySAM model outputs if True
    @returns debt_fraction - Calculated debt fraction (% 0-100)
    """
    # Partnership flip with debt (tax-equity financing)
    model = levpartflip.default("GenericSystemLeveragedPartnershipFlip")

    # Values required for computation. Set to pysam using model.value() calls below
    analysis_period = 20
    ac_capacity = 1000  # kW
    capacity_factor = input_vals["CF"]
    gen = [
        capacity_factor * ac_capacity
    ] * 8760  # Distribute evenly throughout the year

    capex = input_vals["OCC"]
    con_fin_costs = input_vals["CFC"]
    initial_investment = capex * ac_capacity
    con_fin_total = con_fin_costs * ac_capacity
    o_and_m = input_vals["Fixed O&M"]
    v_o_and_m = input_vals["Variable O&M"]
    dscr = input_vals["DSCR"]

    ## Set these here so we can adjust below
    tax_federal = input_vals["Tax Rate (Federal and State)"] * 100
    tax_state = 0
    inflation = input_vals["Inflation Rate"] * 100

    degradation = 0.0  # ATB presents average capactity factors, so zero out degradation

    # Setting PySAM variables. See https://nrel-pysam.readthedocs.io/en/main/modules/Levpartflip.html for docs
    model.value("analysis_period", analysis_period)
    model.value("flip_target_year", analysis_period)
    model.value("gen", gen)
    model.value("system_capacity", ac_capacity)
    model.value("total_installed_cost", initial_investment)

    ## Single Owner will apply the O&M cost to each year, so no need to multiply by analysis period
    model.value("om_capacity", [o_and_m])
    model.value("om_production", [v_o_and_m])
    if "Fuel" in input_vals:
        model.value("om_fuel_cost", [input_vals["Fuel"]])
    if "Heat Rate" in input_vals:
        model.value("system_heat_rate", input_vals["Heat Rate"])

    # Specify length 1 so degradation is applied each year.
    # An array of 0.7 len(analysis_period) assumes degradation the first year, but not afterwards
    model.value("degradation", [degradation])
    model.value(
        "system_use_lifetime_output", 0
    )  # Do degradation in the financial model

    model.value(
        "debt_option", 1
    )  # Use DSCR (alternative is to specify the debt fraction, which doesn't help)
    model.value("dscr", dscr)
    model.value("inflation_rate", inflation)
    model.value("term_int_rate", input_vals["Interest Rate Nominal"] * 100)
    model.value("term_tenor", 18)  # years
    model.value(
        "real_discount_rate",
        input_vals["Calculated Rate of Return on Equity Real"] * 100,
    )
    model.value(
        "flip_target_percent", input_vals["Rate of Return on Equity Nominal"] * 100
    )  ## "nominal equity rate"
    model.value("flip_target_year", 10)  # Assume flip occurs when PTC expires
    model.value("ppa_escalation", 0.0)

    model.value("tax_investor_preflip_cash_percent", 90.0)
    model.value("tax_investor_preflip_tax_percent", 90.0)
    model.value("tax_investor_equity_percent", 90.0)
    model.value("tax_investor_postflip_cash_percent", 10.0)
    model.value("tax_investor_postflip_tax_percent", 10.0)

    model.value("federal_tax_rate", [tax_federal])
    model.value("state_tax_rate", [tax_state])

    # This group is included in fixed O&M
    model.value("insurance_rate", 0)
    model.value("property_tax_rate", 0)
    model.value("prop_tax_cost_assessed_percent", 0)

    model.value("reserves_interest", 0)
    model.value("salvage_percentage", 0)
    model.value("months_receivables_reserve", 0)
    model.value("months_working_reserve", 0)
    model.value("dscr_reserve_months", 0)
    model.value("equip1_reserve_cost", 0)
    model.value("equip2_reserve_cost", 0)
    model.value("equip3_reserve_cost", 0)
    model.value("cost_debt_closing", 0)
    model.value("cost_debt_fee", 0)
    model.value("loan_moratorium", 0)
    model.value("construction_financing_cost", con_fin_total)
    model.value("itc_fed_percent", [input_vals["ITC"] * 100])
    model.value("itc_fed_percent_maxvalue", [1e38])
    model.value("itc_sta_amount", [0])
    model.value("ptc_fed_amount", [input_vals["PTC"] / 1000])  # Convert $/MWh to $/kWh

    # Production based incentive code to test treating the tax credits as available for debt service, currently unused
    model.value("pbi_fed_amount", [0])
    model.value("pbi_fed_term", 0)
    model.value("pbi_fed_escal", 2.5)
    model.value("pbi_fed_for_ds", True)
    model.value("pbi_fed_tax_fed", False)
    model.value("pbi_fed_tax_sta", False)

    # Convert ATB deprecation fields to SAM depreciation. Set ITC basis equal to 100% of CAPEX in
    # all cases.
    if input_vals["MACRS"] == MACRS_6:
        model.value("depr_alloc_macrs_5_percent", 100)
        model.value("depr_itc_fed_macrs_5", 1)
        model.value("depr_itc_sta_macrs_5", 1)
        model.value("depr_alloc_macrs_15_percent", 0)
        model.value("depr_alloc_sl_20_percent", 0)
    elif input_vals["MACRS"] == MACRS_16:
        model.value("depr_alloc_macrs_5_percent", 0)
        model.value("depr_alloc_macrs_15_percent", 100)
        model.value("depr_itc_fed_macrs_15", 1)
        model.value("depr_itc_sta_macrs_15", 1)
        model.value("depr_alloc_sl_20_percent", 0)
    elif input_vals["MACRS"] == MACRS_21:
        model.value("depr_alloc_macrs_5_percent", 0)
        model.value("depr_alloc_macrs_15_percent", 0)
        model.value("depr_alloc_sl_20_percent", 100)
        model.value("depr_itc_fed_sl_20", 1)
        model.value("depr_itc_fed_sl_20", 1)
    else:
        raise ValueError(
            "MACRS is expected to be one of MACRS_6, MACRS_16, or MACRS_21. "
            f'Unknown value provided: {input_vals["MACRS"]}'
        )

    # Turn off unused depreciation features
    model.value("depr_alloc_custom_percent", 0)
    model.value("depr_alloc_sl_5_percent", 0)
    model.value("depr_alloc_sl_15_percent", 0)
    model.value("depr_alloc_sl_39_percent", 0)
    model.value("depr_bonus_fed", 0)
    model.value("depr_bonus_sta", 0)
    model.value("depr_bonus_fed_macrs_5", 0)
    model.value("depr_bonus_sta_macrs_5", 0)
    model.value("depr_bonus_fed_macrs_15", 0)
    model.value("depr_bonus_sta_macrs_15", 0)

    model.value("depr_fedbas_method", 0)
    model.value("depr_stabas_method", 0)

    model.value("ppa_soln_mode", 0)  # Solve for PPA price given IRR
    model.value("payment_option", 0)  # Equal payments (standard amoritization)

    # Required for calculate PPA price.
    # Default is $0.045/kWh. However given the way we've set up gen, this will never be used
    model.value("en_electricity_rates", 1)

    model.execute()

    if debug:
        print(
            f"LCOE: {model.Outputs.lcoe_real} cents/kWh"
        )  # multiply by 10 to get $ / MWh
        print(f"NPV: {model.Outputs.cf_project_return_aftertax_npv}")
        print()
        print(f"IRR in target year: {model.Outputs.flip_target_irr}")
        print(f"IRR at end of project: {model.Outputs.analysis_period_irr}")
        print(f"O&M: {model.Outputs.cf_om_capacity_expense}")
        print(f"PPA price: {model.Outputs.cf_ppa_price}")
        print(f"Debt Principal: {model.Outputs.cf_debt_payment_principal}")
        print(f"Debt Interest: {model.Outputs.cf_debt_payment_interest}")
        print(f"Depreciation: {model.Outputs.cf_feddepr_total}")
        print(f"Production: {model.Outputs.cf_energy_net}")
        print(f"Tax {model.Outputs.cf_fedtax}")
        print(f"ITC {model.Outputs.itc_total_fed}")
        print(f"PTC {model.Outputs.cf_ptc_fed}")
        print(f"Debt fraction {model.Outputs.debt_fraction}")
        print()

    return model.Outputs.debt_fraction


tech_names = [Tech.__name__ for Tech in LCOE_TECHS]


@click.command
@click.argument("data_workbook_filename", type=click.Path(exists=True))
@click.argument("output_filename", type=click.Path(exists=False))
@click.option(
    "-t",
    "--tech",
    type=click.Choice(tech_names),
    help="Name of technology to calculate debt fraction for. Use all techs if none are "
    "specified. Only technologies with an LCOE may be processed.",
)
@click.option("-d", "--debug", is_flag=True, default=False, help="Print debug data.")
def calculate_all_debt_fractions(
    data_workbook_filename: str, output_filename: str, tech: str | None, debug: bool
):
    """
    Calculate debt fractions for one or more technologies, and all financial cases and years.

    DATA_WORKBOOK_FILENAME - Path and name of ATB data workbook XLXS file.
    OUTPUT_FILENAME - File to save calculated debt fractions to. Should end with .csv
    """
    tech_map: Dict[str, Type[TechProcessor]] = {
        tech.__name__: tech for tech in LCOE_TECHS
    }
    techs = LCOE_TECHS if tech is None else [tech_map[tech]]

    df_itc, df_ptc = Extractor.get_tax_credits_sheet(data_workbook_filename)

    crp: CrpChoiceType = 20
    debt_frac_dict = {}

    for Tech in techs:
        tech_years = range(Tech.base_year, END_YEAR + 1)

        # column structure of resulting data frame
        cols = ["Technology", "Case"] + [str(year) for year in tech_years]

        for fin_case in FINANCIAL_CASES:
            click.echo(
                f"Processing tech {Tech.tech_name} and financial case {fin_case}"
            )
            debt_fracs = [Tech.tech_name, fin_case]  # First two columns are metadata

            proc = Tech(
                data_workbook_filename,
                crp=crp,
                case=fin_case,
                tcc=PTC_PLUS_ITC_CASE_PVB,
            )
            proc.run()

            d = proc.flat

            # Values that are specific to the representative tech detail
            detail_vals = d[
                (d.DisplayName == Tech.default_tech_detail)
                & (d.Case == fin_case)
                & (d.Scenario == "Moderate")
                & (d.CRPYears == 20)
                & (
                    (d.Parameter == "Fixed O&M")
                    | (d.Parameter == "Variable O&M")
                    | (d.Parameter == "OCC")
                    | (d.Parameter == "CFC")
                    | (d.Parameter == "CF")
                    | (d.Parameter == "Heat Rate")
                    | (d.Parameter == "Fuel")
                )
            ]

            # Values that apply to entire technology
            tech_vals = d[
                (d.Technology == Tech.tech_name)
                & (d.CRPYears == 20)
                & (d.Case == fin_case)
                & (
                    (d.Parameter == "Inflation Rate")
                    | (d.Parameter == "Tax Rate (Federal and State)")
                    | (d.Parameter == "Calculated Rate of Return on Equity Real")
                    | (d.Parameter == "Rate of Return on Equity Nominal")
                    | (d.Parameter == "Interest Rate Nominal")
                )
            ]

            for year in tech_years:
                if debug:
                    click.echo(
                        f"Processing tech {Tech.tech_name}, financial case {fin_case}, "
                        f"and year {year}"
                    )
                if not year in detail_vals or not year in tech_vals:
                    debt_fracs.append(None)
                    continue

                input_vals = detail_vals.set_index("Parameter")[year].to_dict()
                gen_vals = tech_vals.set_index("Parameter")[year].to_dict()

                # Tax credits - assumes each tech has one PTC or one ITC
                if Tech.has_tax_credit and fin_case == "Market":
                    name = str(Tech.sheet_name)
                    if Tech.wacc_name:
                        name = Tech.wacc_name

                    if Tech.sheet_name == "Utility-Scale PV-Plus-Battery":
                        if (
                            proc.tax_credit_case is PTC_PLUS_ITC_CASE_PVB
                            and year > 2022
                        ):
                            if Tech.default_tech_detail is None:
                                raise AttributeError(
                                    "Tech.default_tech_detail must be set for "
                                )
                            ncf = proc.df_ncf.loc[
                                Tech.default_tech_detail + "/Moderate"
                            ][year]
                            pvcf = proc.df_pvcf.loc[
                                Tech.default_tech_detail + "/Moderate"
                            ][year]

                            batt_occ_percent = (
                                proc.df_batt_cost
                                * proc.CO_LOCATION_SAVINGS
                                / proc.df_occ
                            )

                            input_vals["PTC"] = df_ptc.loc[name][year] * min(
                                ncf / pvcf, 1.0
                            )
                            input_vals["ITC"] = (
                                df_itc.loc[name][year]
                                * batt_occ_percent.loc[
                                    Tech.default_tech_detail + "/Moderate"
                                ][year]
                            )
                        else:
                            input_vals["PTC"] = 0
                            input_vals["ITC"] = df_itc.loc[name][year]
                    else:
                        input_vals["PTC"] = df_ptc.loc[name][year]
                        input_vals["ITC"] = df_itc.loc[name][year]
                else:
                    input_vals["PTC"] = 0
                    input_vals["ITC"] = 0

                # Financial parameters stored in tech processor
                input_vals["DSCR"] = Tech.dscr

                input_vals["MACRS"] = proc.get_depreciation_schedule(year)

                input_vals.update(gen_vals)

                # Calculate debt fraction using PySAM
                debt_frac = calculate_debt_fraction(input_vals, debug)
                debt_frac /= 100.0
                debt_fracs.append(debt_frac)

            debt_frac_dict[proc.tech_name + fin_case] = debt_fracs

    debt_frac_df = pd.DataFrame.from_dict(debt_frac_dict, orient="index", columns=cols)
    debt_frac_df.to_csv(output_filename)


if __name__ == "__main__":
    calculate_all_debt_fractions()  # pylint: disable=no-value-for-parameter
