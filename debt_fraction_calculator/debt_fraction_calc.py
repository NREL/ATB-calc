import pandas as pd
import numpy as np
import PySAM.Singleowner as singleowner

model = singleowner.default("GenericSystemSingleOwner")

analysis_period = 20
ac_capacity = 1000 # kW
capacity_factor = 0.25
gen = [capacity_factor * ac_capacity] * 8760 # Distribute evenly throughout the year

print(len(gen))

capex = 1139
con_fin_costs = 31
initial_investment = capex * ac_capacity
con_fin_total = con_fin_costs * ac_capacity
o_and_m = 21
dscr = 1.3

## Set these here so we can adjust below
irr_target = 7.75 ## for real discount rate = 5.12 and inflation = 2.25, this is equal to nominal discount rate
tax_federal = 25.74
tax_state = 0
inflation = 2.5

degradation = 0.0 # ATB presents average capactity factors

model.value("analysis_period", analysis_period)
model.value("flip_target_year", analysis_period)
model.value("gen", gen)
model.value("system_pre_curtailment_kwac", gen)
model.value("system_capacity", ac_capacity)
model.value("cp_system_nameplate", ac_capacity / 1000)
model.value("total_installed_cost", initial_investment)

## Single Owner should apply the O&M cost to each year, so no need to multiply by analysis period?
model.value("om_capacity", [o_and_m] ) 

model.value("degradation", [degradation]) # Specify length 1 so degradation is applied each year. An array of 0.7 len(analysis_period) assumes degradation the first year, but not afterwards
model.value("system_use_lifetime_output", 0) # Do degradation in the financial model

model.value("debt_option", 1) # Use Debt Percent instead of DSCR
model.value("dscr", dscr)
# model.value("debt_percent", 51.9)
model.value("inflation_rate", inflation)
model.value("term_int_rate", 5.0)
model.value("term_tenor", 18)
model.value("real_discount_rate", 4.9) ## "real equity rate"
model.value("flip_target_percent", irr_target) ## "nominal equity rate"
model.value("ppa_escalation", 0.0)

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
model.value("itc_fed_percent", [0])
model.value("itc_sta_amount", [0])
model.value("ptc_fed_amount", [0.0275])

model.value("depr_alloc_macrs_5_percent", 100)
model.value("depr_alloc_custom_percent", 0)
model.value("depr_alloc_macrs_15_percent", 0)
model.value("depr_alloc_sl_5_percent", 0)
model.value("depr_alloc_sl_15_percent", 0)
model.value("depr_alloc_sl_20_percent", 0)
model.value("depr_alloc_sl_39_percent", 0)
model.value("depr_bonus_fed", 0)
model.value("depr_bonus_sta", 0)
model.value("depr_bonus_fed_macrs_5", 0)
model.value("depr_bonus_sta_macrs_5", 0)
model.value("depr_itc_fed_macrs_5", 0)
model.value("depr_itc_sta_macrs_5", 0)
model.value("depr_bonus_fed_macrs_15", 0)
model.value("depr_bonus_sta_macrs_15", 0)
model.value("depr_itc_fed_macrs_15", 0)
model.value("depr_itc_sta_macrs_15", 0)
model.value("depr_fedbas_method", 0)
model.value("depr_stabas_method", 0)

model.value("ppa_soln_mode", 0)
model.value("payment_option", 0)

model.value('en_electricity_rates', 1 )

## Test 1: Reserve accounts are all set to zero

model.execute()

arr = model.Outputs.cf_project_investing_activities
test = sum(arr);
print("Test for reserve accounts (0 is passing): " + str( initial_investment + test ) )

## Test 2: LCOE is independent of revenue when no taxes

model.value("federal_tax_rate", [0])
model.value("state_tax_rate", [0])

model.value("flip_target_percent", irr_target)
model.execute()

lcoe_a = model.Outputs.lcoe_real;

model.value("flip_target_percent", irr_target*1.5)
model.execute()

lcoe_b = model.Outputs.lcoe_real;
print("Test for LCOE independent of revenue (1 is passing): " + str( lcoe_a / lcoe_b ) ) 
print()

model.value("federal_tax_rate", [tax_federal])
model.value("state_tax_rate", [tax_state])
model.value("flip_target_percent", irr_target)

## Results with cash flow line items for troubleshooting

model.execute()

print("LCOE: " + str(model.Outputs.lcoe_real)) #Cents / kWh - multiply by 10 to get $ / MWh
print("NPV: " + str(model.Outputs.project_return_aftertax_npv))
print()
print("IRR in target year: " + str(model.Outputs.flip_target_irr))
print("IRR at end of project: " + str(model.Outputs.analysis_period_irr))
print("O&M: " + str(model.Outputs.cf_om_capacity_expense))
print("Debt Principal: " + str(model.Outputs.cf_debt_payment_principal))
print("Debt Interest: " + str(model.Outputs.cf_debt_payment_interest))
print("Depreciation: " + str(model.Outputs.cf_feddepr_total))
print("Production: " + str(model.Outputs.cf_energy_net))
print("Debt fraction " + str(model.Outputs.debt_fraction))

