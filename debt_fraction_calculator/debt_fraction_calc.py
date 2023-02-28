"""
Workflow to calculate debt fractions based on scraped data

Developed against PySAM 4.0.0
"""

import pandas as pd
import numpy as np
import PySAM.Levpartflip as levpartflip

from extractor import Extractor, YEARS, FIN_CASES

# Import processors that calculate LCOE
from tech_processors import OffShoreWindProc, LandBasedWindProc, DistributedWindProc,\
    UtilityPvProc, CommPvProc, ResPvProc, UtilityPvPlusBatteryProc,\
    CspProc, GeothermalProc, HydropowerProc,\
    NuclearProc, BiopowerProc

from macrs import MACRS_6, MACRS_16, MACRS_21

def calculate_debt_fraction(input_vals, debug=False):
    """
    Expected fields for dict input_values. Required unless indicated otherwise:
        CF - capacity factor (%, 0-1)
        OCC - overnight capital cost ($/kW)
        CFC - construction financing cost ($/kW)
        Fixed O&M - fixed operations and maintenance ($/kW-yr)
        Variable O&M - variable operations and maintenance ($/Mwh)
        DSCR - Debt service coverage ratio (unitless, typically 1-1.5)
        IRR - internal rate of return (%, 0-100)
        Tax Rate (Federal and State) (%, 0-1)
        Inflation Rate (%, 0-1)
        Fuel - Fuel cost ($/MMBtu) - optional
        Heat Rate - (MMBtu/MWh) - optional
        Interest Rate Nominal (%, 0-1)
        Calculated Rate of Return on Equity Real (%, 0-1)
        ITC - Investment tax Credit, federal (%, 0-1)
        PTC - Production tax credit, federal ($/MWh)
    
    Returns debt_fraction, float, (% 0-100)
    """
    model = levpartflip.default("GenericSystemLeveragedPartnershipFlip")

    # Values required for computation. Additional input values used directly in model.value calls
    analysis_period = 20
    ac_capacity = 1000 # kW
    capacity_factor = input_vals["CF"]
    gen = [capacity_factor * ac_capacity] * 8760 # Distribute evenly throughout the year

    capex = input_vals["OCC"]
    con_fin_costs = input_vals["CFC"]
    initial_investment = capex * ac_capacity
    con_fin_total = con_fin_costs * ac_capacity
    o_and_m = input_vals["Fixed O&M"]
    v_o_and_m = input_vals["Variable O&M"]
    dscr = input_vals["DSCR"]

    ## Set these here so we can adjust below
    irr_target = input_vals["IRR"] 
    tax_federal = input_vals["Tax Rate (Federal and State)"] * 100
    tax_state = 0
    inflation = input_vals["Inflation Rate"] * 100

    degradation = 0.0 # ATB presents average capactity factors, so zero out degradation

    model.value("analysis_period", analysis_period)
    model.value("flip_target_year", analysis_period)
    model.value("gen", gen)
    #model.value("system_pre_curtailment_kwac", gen)
    model.value("system_capacity", ac_capacity)
    #model.value("cp_system_nameplate", ac_capacity / 1000)
    model.value("total_installed_cost", initial_investment)

    ## Single Owner will apply the O&M cost to each year, so no need to multiply by analysis period
    model.value("om_capacity", [o_and_m] ) 
    model.value("om_production", [v_o_and_m])
    if 'Fuel' in input_vals:
        model.value("om_fuel_cost", [input_vals['Fuel']])
    if 'Heat Rate' in input_vals:
        model.value("system_heat_rate", input_vals['Heat Rate'])

    # Specify length 1 so degradation is applied each year.
    # An array of 0.7 len(analysis_period) assumes degradation the first year, but not afterwards
    model.value("degradation", [degradation]) 
    model.value("system_use_lifetime_output", 0) # Do degradation in the financial model

    model.value("debt_option", 1) # Use DSCR (alternative is to specify the debt fraction, which doesn't help)
    model.value("dscr", dscr)
    model.value("inflation_rate", inflation)
    model.value("term_int_rate", input_vals['Interest Rate Nominal'] * 100)
    model.value("term_tenor", 18) # years
    model.value("real_discount_rate", input_vals['Calculated Rate of Return on Equity Real'] * 100) 
    model.value("flip_target_percent", irr_target) ## "nominal equity rate"
    model.value("flip_target_year", 10) # Assume flip occurs when PTC expires
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
    model.value('itc_fed_percent_maxvalue', [1e38])
    model.value("itc_sta_amount", [0])
    model.value("ptc_fed_amount", [input_vals["PTC"] / 1000]) # Convert $/MWh to $/kWh
    
    # Production based incentive code to test treating the tax credits as available for debt service
    model.value("pbi_fed_amount", [0])
    model.value("pbi_fed_term", 0)
    model.value("pbi_fed_escal", 2.5)
    model.value("pbi_fed_for_ds", True)
    model.value("pbi_fed_tax_fed", False)
    model.value("pbi_fed_tax_sta", False)

    # Convert ATB deprecation fields to SAM depreciation. Set ITC basis equal to 100% of CAPEX in all cases
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

    model.value("ppa_soln_mode", 0)
    model.value("payment_option", 0)

    # Required for calculate PPA price. 
    # Default is $0.045/kWh. However given the way we've set up gen, this will never be used 
    model.value('en_electricity_rates', 1 ) 

    model.execute()

    if debug:
        print(f"LCOE: {model.Outputs.lcoe_real}") #Cents / kWh - multiply by 10 to get $ / MWh
        print(f"NPV: {model.Outputs.project_return_aftertax_npv}")
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

    return model.Outputs.debt_fraction

if __name__ == "__main__":
    # Start by running the scrape for relevant technologies
    # Data master version on sharepoint - empty string if you haven't renamed the file
    version_string = "_v2.70"

    # Path to data master spreadsheet
    data_master_filename = '../2023-ATB-Data_Master' + version_string + '.xlsx'

    # Techs will both be scraped and have debt fractions calculated
    techs = [
                    OffShoreWindProc, LandBasedWindProc, DistributedWindProc,
                    UtilityPvProc, CommPvProc, ResPvProc, UtilityPvPlusBatteryProc,
                    CspProc, GeothermalProc, HydropowerProc, NuclearProc, BiopowerProc
                ]

    df_itc, df_ptc = Extractor.get_tax_credits_sheet(data_master_filename)

    crp = 20

    debt_frac_dict = {}

    cols = ["Technology", "Case", *YEARS] # column structure of resulting data frame

    for tech in techs:
        for fin_case in FIN_CASES:
            print("Tech ", tech.tech_name, "Fin case " , fin_case)
            debt_fracs = [tech.tech_name, fin_case] # First two columns are metadata
        
            proc = tech(data_master_filename, crp=crp, case=fin_case)
            proc.run()
            
            d = proc.flat

            # Values that are specific to the representative tech detail
            detail_vals = d[(d.DisplayName == tech.default_tech_detail) & (d.Case == fin_case) 
                    & (d.Scenario == 'Moderate') & (d.CRPYears == 20) & 
                    ((d.Parameter == 'Fixed O&M') | (d.Parameter == 'Variable O&M') 
                    | (d.Parameter == 'OCC') | (d.Parameter == 'CFC') | (d.Parameter == 'CF')
                    | (d.Parameter == 'Heat Rate') | (d.Parameter == 'Fuel'))]

            # Values that apply to entire technology
            tech_vals = d[(d.Technology == tech.tech_name) & (d.CRPYears == 20) & (d.Case == fin_case) & 
                    ((d.Parameter == 'Inflation Rate') | (d.Parameter == 'Tax Rate (Federal and State)') 
                    | (d.Parameter == 'Calculated Rate of Return on Equity Real') 
                    | (d.Parameter == 'Interest Rate Nominal'))]

            for year in YEARS:            
                input_vals = detail_vals.set_index('Parameter')[year].to_dict()

                gen_vals = tech_vals.set_index('Parameter')[year].to_dict()

                # Tax credits
                if tech.has_itc and tech.has_ptc and fin_case == 'Market':
                    input_vals["PTC"] = df_ptc.loc[tech.sheet_name][year]
                    input_vals["ITC"] = df_itc.loc[tech.sheet_name][year]
                else:
                    input_vals["PTC"] = 0
                    input_vals["ITC"] = 0
                
                # Financial parameters stored in tech processor
                input_vals["DSCR"] = tech.dscr
                input_vals["IRR"] = tech.irr_target

                input_vals["MACRS"] = proc.get_depreciation_schedule(year)

                input_vals.update(gen_vals)

                #Calculate debt fraction using PySAM
                debt_frac = calculate_debt_fraction(input_vals)

                debt_frac /= 100.0                
                debt_fracs.append(debt_frac)
            
            debt_frac_dict[tech.tech_name + fin_case] = debt_fracs

    debt_frac_df = pd.DataFrame.from_dict(debt_frac_dict, orient='index', columns=cols)
    debt_frac_df.to_csv("2023_debt_fractions" + version_string + ".csv")