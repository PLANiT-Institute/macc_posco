# tests/test_optimizer.py

import os
import pytest
from src.data_manager import DataManager
from src.model_config import ModelConfig
from src.optimizer import Optimizer

@pytest.fixture
def setup_data_manager():
    # Adjust path as needed
    data_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'posco_dynamics_v1.0.xlsx')
    dm = DataManager(data_file_path)
    dm.load_data()
    return dm

def test_optimizer_runs(setup_data_manager):
    dm = setup_data_manager
    config = ModelConfig(
        start_year=2024,
        end_year=2025,  # shortened range for a quick test
        discount_rate=0.05,
        num_technologies=4,
        scenarios=['below_2'],
        allowance_scenarios=['allow_scenario_1'],
        results_dir="test_results"
    )

    optimizer = Optimizer(dm, config)
    results = optimizer.solve_for_scenarios()

    # We expect at least one scenario result
    assert len(results) == 1
    scenario_key = ('below_2', 'allow_scenario_1')
    assert scenario_key in results

    # Basic checks
    assert results[scenario_key]['status'] in ["Optimal", "Feasible", "Not Solved"], "Unexpected solver status."
    assert results[scenario_key]['objective_value'] is not None, "No objective value returned."
