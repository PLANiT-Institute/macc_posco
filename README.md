# POSCO MACC Optimization Model

This repository contains a class-based Python project to model and optimize steelmaking pathways under different carbon-price **scenarios**. It reads data from an Excel file (`posco_dynamics_v1.0.xlsx`) with multiple sheets for:
- **facility**: facilities, capacities, end-of-life years 
- **tech_mac**: marginal abatement cost (MAC) by year and technology 
- **tech_emission**: emission intensity by year and technology 
- **carbon_price**: carbon prices by year for different scenarios (e.g., below_2, ndc, net_zero)

> **Note:** There is **no** allowance logic in this model. All references to allowances were removed.

## Project Structure

- **data**: Contains the input Excel file.
- **main**: Contains `run_optimization.py`, the main entry point to run the pipeline.
- **results**: Generated output such as CSV files and plots.
- **src**: Source code for:
  - `data_manager.py`: Reads/organizes data from Excel.
  - `model_config.py`: Holds model-level configuration (start year, end year, etc.).
  - `optimizer.py`: Defines the linear optimization problem using [PuLP](https://pypi.org/project/PuLP/).
  - `utils.py`: Utility functions such as logging setup.
- **tests**: Basic unit tests (using [pytest](https://pypi.org/project/pytest/)).
