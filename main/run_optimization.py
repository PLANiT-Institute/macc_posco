# main/run_optimization.py

import os
import pandas as pd
import matplotlib.pyplot as plt

from src.data_manager import DataManager
from src.model_config import ModelConfig
from src.optimizer import Optimizer
from src.utils import setup_logging

def main():
    logger = setup_logging()

    # 1) Define file paths
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    data_file_path = os.path.join(root_dir, 'data', 'posco_dynamics_v1.0.xlsx')

    # 2) Load data
    dm = DataManager(data_file_path)
    dm.load_data()
    logger.info("Data loaded successfully.")

    # 3) Model config
    config = ModelConfig(
        start_year=2024,
        end_year=2050,
        discount_rate=0.05,
        scenarios=['below_2', 'ndc', 'net_zero'],  # same as single-file
        results_dir="results2_posco"
    )
    logger.info(f"Using ModelConfig: {config}")

    # 4) Instantiate optimizer and solve for each scenario
    optimizer = Optimizer(dm, config)
    results = optimizer.solve_for_scenarios()
    logger.info("Optimization completed for all scenarios.")

    # 5) Build emission paths
    facility_df = dm.facility_data
    technologies = optimizer.technologies
    scenario_emission_paths = {}

    for scenario, res in results.items():
        decisions = res['decisions']
        start_y = config.start_year
        end_y   = config.end_year

        # sum up total emissions
        path_list = []
        for year in range(start_y, end_y + 1):
            total_emi = 0.0
            for i in range(len(facility_df)):
                chosen_tech = decisions[(i, year)]
                cap_i = facility_df.loc[i, 'capacity']
                emi_int = dm.get_emission_intensity(year, chosen_tech)
                total_emi += cap_i * emi_int
            path_list.append((year, total_emi))
        scenario_emission_paths[scenario] = path_list

    # 6) Create results dir
    results_dir = os.path.join(root_dir, config.results_dir)
    os.makedirs(results_dir, exist_ok=True)

    # 7) Save each scenario's emission path
    for scenario, path_data in scenario_emission_paths.items():
        df = pd.DataFrame(path_data, columns=['Year','Total_Emissions'])
        df.to_csv(os.path.join(results_dir, f"emission_path_{scenario}.csv"), index=False)

        # Plot
        years, emissions = zip(*path_data)
        plt.figure(figsize=(12,6))
        plt.plot(years, emissions, marker='o', label=scenario)
        plt.title(f"Emission Path: {scenario}")
        plt.xlabel("Year")
        plt.ylabel("Total Emissions")
        plt.grid(True)
        plt.legend()
        plt.savefig(os.path.join(results_dir, f"emission_path_{scenario}.png"))
        plt.close()

    # Summaries
    summary_data = []
    for scenario, res in results.items():
        summary_data.append({
            'Scenario': scenario,
            'Status': res['status'],
            'Objective_Value': res['objective_value']
        })
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(os.path.join(results_dir, "npv_results_summary.csv"), index=False)

    # Combined emission paths
    plt.figure(figsize=(12,6))
    combined_df = pd.DataFrame({'Year': [y for y in range(config.start_year, config.end_year+1)]})
    for scenario, path_data in scenario_emission_paths.items():
        years, emissions = zip(*path_data)
        plt.plot(years, emissions, marker='o', label=scenario)
        combined_df[f'{scenario}_Emissions'] = emissions
    plt.title("Emission Paths for Different Scenarios")
    plt.xlabel("Year")
    plt.ylabel("Total Emissions")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(results_dir, "emission_paths_combined.png"))
    plt.close()

    combined_df.to_csv(os.path.join(results_dir, "emission_paths_table.csv"), index=False)

    logger.info("\nNPV Results:\n%s", summary_df)
    logger.info("Saved all results in '%s'", results_dir)

if __name__ == "__main__":
    main()
