import os
import pulp
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
#                1. Load Input Data
# ============================================================

DATA_FILE = 'data/posco_dynamics_v1.0.xlsx'
RESULTS_DIR = 'results_posco'
os.makedirs(RESULTS_DIR, exist_ok=True)

facility_data       = pd.read_excel(DATA_FILE, sheet_name='facility')
tech_mac_data       = pd.read_excel(DATA_FILE, sheet_name='tech_mac')
tech_emission_data  = pd.read_excel(DATA_FILE, sheet_name='tech_emission')
allowance_rate_data = pd.read_excel(DATA_FILE, sheet_name='allowance_rate')
carbon_price_data   = pd.read_excel(DATA_FILE, sheet_name='carbon_price')

# We assume allowance_rate_data has columns: ['year', 'allow_rate']
# We assume carbon_price_data has columns: ['year', 'below_2', 'ndc', 'net_zero']
# We assume facility_data has columns: ['facility_id', 'capacity', 'end_year'] or 'end-year'

# ============================================================
#                2. Define Constants and Helpers
# ============================================================

START_YEAR = 2024
END_YEAR   = 2050
DISCOUNT_RATE = 0.05

SCENARIOS = ['below_2', 'ndc', 'net_zero']

NUM_FACILITIES = len(facility_data)
TECHNOLOGIES   = ['BF_BOF', 'BF_BOF_scrap', 'BF_BOF_CCUS', 'H2_HDRI_EAF']  # Index 3 = H2

def get_carbon_price(year, scenario):
    row = carbon_price_data.loc[carbon_price_data['year'] == year, scenario]
    if row.empty:
        raise ValueError(f"No carbon price for year={year}, scenario={scenario}")
    return float(row.values[0])

def get_allow_rate(year):
    # Single column named 'allow_rate', returns fraction like 0.10 if 10%
    row = allowance_rate_data.loc[allowance_rate_data['year'] == year, 'allow_rate']
    if row.empty:
        raise ValueError(f"No allow_rate data for year={year}")
    return float(row.values[0])

def get_emission_intensity(year, tech):
    row = tech_emission_data.loc[tech_emission_data['year'] == year, tech]
    if row.empty:
        raise ValueError(f"No emission intensity for year={year}, tech={tech}")
    return float(row.values[0])

def get_mac(year, tech):
    row = tech_mac_data.loc[tech_mac_data['year'] == year, tech]
    if row.empty:
        raise ValueError(f"No MAC data for year={year}, tech={tech}")
    return float(row.values[0])

# ============================================================
#      3. Build a Single Problem, Then Solve for Each Scenario
# ============================================================

# Create a single problem object. We'll set different objectives for each scenario.
prob = pulp.LpProblem("Emission_Path_Optimization", pulp.LpMinimize)

# Decision variables: x[i, t, y] ∈ {0,1}
x = pulp.LpVariable.dicts(
    "tech_choice",
    ((i, t, y) for i in range(NUM_FACILITIES)
               for t in range(len(TECHNOLOGIES))
               for y in range(START_YEAR, END_YEAR + 1)),
    cat='Binary'
)

# ============================================================
#                4. Constraints
# ============================================================

# 4.1 Exactly one technology per facility-year
for i in range(NUM_FACILITIES):
    for y in range(START_YEAR, END_YEAR + 1):
        prob += pulp.lpSum(x[i, t, y] for t in range(len(TECHNOLOGIES))) == 1

# 4.2 Force H2_HDRI_EAF (index 3) after facility's end_year
for i in range(NUM_FACILITIES):
    # Adjust the column name if it's 'end-year' vs 'end_year'
    facility_end = facility_data.loc[i, 'end_year']
    # For years from facility_end to END_YEAR, we fix x[i, 3, y] = 1
    if facility_end <= END_YEAR:
        for y in range(int(facility_end), END_YEAR + 1):
            prob += x[i, 3, y] == 1
            # also forces other techs = 0
            for t_other in range(len(TECHNOLOGIES)):
                if t_other != 3:
                    prob += x[i, t_other, y] == 0

# ============================================================
#   5. Build Separate Objective for Each Scenario, Solve, Store
# ============================================================

results = {}
objectives = {}

for scenario in SCENARIOS:
    # Build objective expression
    cost_expr = []
    for i in range(NUM_FACILITIES):
        cap_i = facility_data.loc[i, 'capacity']
        for y in range(START_YEAR, END_YEAR + 1):
            discount_factor = 1.0 / ((1.0 + DISCOUNT_RATE)**(y - START_YEAR))
            for t, tech_name in enumerate(TECHNOLOGIES):
                # Carbon cost
                carbon_p = get_carbon_price(y, scenario)
                emi_int  = get_emission_intensity(y, tech_name)

                # Subtract free allowance cost
                allow_fraction = get_allow_rate(y)
                # => net carbon cost = capacity * emission_intensity * carbon_price * (1 - allowance_fraction)
                # We'll do it explicitly:
                carbon_cost = cap_i * emi_int * carbon_p
                allowance_offset = cap_i * emi_int * carbon_p * allow_fraction

                # Abatement cost
                # (BF_BOF_intensity - tech_intensity) * MAC, times capacity
                bf_bof_int  = get_emission_intensity(y, 'BF_BOF')
                tech_mac_val= get_mac(y, tech_name)
                abatement   = cap_i * (bf_bof_int - emi_int) * tech_mac_val

                # total cost in year y, with discount
                total_cost_y = (carbon_cost - allowance_offset + abatement) * discount_factor
                cost_expr.append(x[i, t, y] * total_cost_y)

    objectives[scenario] = pulp.lpSum(cost_expr)

# Now we solve for each scenario by setting the objective, then re‐solving
for scenario in SCENARIOS:
    # Set the objective
    prob.setObjective(objectives[scenario])

    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Collect results
    status = pulp.LpStatus[prob.status]
    objective_value = pulp.value(prob.objective)

    # Decision tracking
    decisions = {}
    for i in range(NUM_FACILITIES):
        for y in range(START_YEAR, END_YEAR + 1):
            for t in range(len(TECHNOLOGIES)):
                if pulp.value(x[i, t, y]) == 1:
                    decisions[(i, y)] = t
                    break

    results[scenario] = {
        'status': status,
        'objective_value': objective_value,
        'decisions': decisions
    }

# ============================================================
#        6. Post-Process: Emission Paths, Output
# ============================================================

emission_paths = {}
for scenario, res in results.items():
    scenario_path = []
    for year in range(START_YEAR, END_YEAR + 1):
        total_emission = 0.0
        for i in range(NUM_FACILITIES):
            chosen_t = res['decisions'][(i, year)]
            chosen_tech = TECHNOLOGIES[chosen_t]
            cap_i = facility_data.loc[i, 'capacity']
            emi_int = get_emission_intensity(year, chosen_tech)
            total_emission += cap_i * emi_int
        scenario_path.append((year, total_emission))
    emission_paths[scenario] = scenario_path

# Save each scenario's emission path
for scenario, path in emission_paths.items():
    df = pd.DataFrame(path, columns=['Year','Total_Emissions'])
    df.to_csv(os.path.join(RESULTS_DIR, f"emission_path_{scenario}.csv"), index=False)

# Plot each scenario separately
for scenario, path in emission_paths.items():
    years, emissions = zip(*path)
    plt.figure(figsize=(12,6))
    plt.plot(years, emissions, marker='o', label=scenario)
    plt.xlabel("Year")
    plt.ylabel("Total Emissions")
    plt.title(f"Emission Path: {scenario}")
    plt.grid(True)
    plt.legend()
    plt.savefig(os.path.join(RESULTS_DIR, f"emission_path_{scenario}.png"))
    plt.close()

# Summaries
npv_results = []
for scenario, res in results.items():
    npv_results.append({
        'Scenario': scenario,
        'Status': res['status'],
        'Objective_Value': res['objective_value']
    })

summary_df = pd.DataFrame(npv_results)
summary_df.to_csv(os.path.join(RESULTS_DIR, "npv_results_summary.csv"), index=False)

# Combined plot
plt.figure(figsize=(12,6))
for scenario, path in emission_paths.items():
    years, emissions = zip(*path)
    plt.plot(years, emissions, marker='o', label=scenario)
plt.title("Emission Paths for Different Scenarios")
plt.xlabel("Year")
plt.ylabel("Total Emissions")
plt.legend()
plt.grid(True)
plt.savefig(os.path.join(RESULTS_DIR, "emission_paths_combined.png"))
plt.close()

# Emissions table
combined_df = pd.DataFrame({'Year': [y for y in range(START_YEAR, END_YEAR+1)]})
for scenario, path in emission_paths.items():
    combined_df[f'{scenario}_Emissions'] = [em for (_, em) in path]
combined_df.to_csv(os.path.join(RESULTS_DIR, "emission_paths_table.csv"), index=False)

# Print summary
print("\nSummary of NPV across Scenarios:")
print(summary_df)
print(f"\nAll results saved in '{RESULTS_DIR}' folder.")
