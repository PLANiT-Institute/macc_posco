# src/data_manager.py

import os
import pandas as pd

class DataManager:
    """
    Class that loads all relevant sheets from the Excel workbook,
    and provides helper functions for cost parameters.
    """

    def __init__(self, data_file_path: str):
        if not os.path.exists(data_file_path):
            raise FileNotFoundError(f"Data file not found: {data_file_path}")
        self.data_file_path = data_file_path

        self.facility_data = None
        self.tech_mac_data = None
        self.tech_emission_data = None
        self.allowance_rate_data = None
        self.carbon_price_data = None

    def load_data(self):
        """Reads all required sheets from the Excel file."""
        self.facility_data = pd.read_excel(self.data_file_path, sheet_name='facility')
        self.tech_mac_data = pd.read_excel(self.data_file_path, sheet_name='tech_mac')
        self.tech_emission_data = pd.read_excel(self.data_file_path, sheet_name='tech_emission')
        self.allowance_rate_data = pd.read_excel(self.data_file_path, sheet_name='allowance_rate')
        self.carbon_price_data = pd.read_excel(self.data_file_path, sheet_name='carbon_price')

    def get_carbon_price(self, year: int, scenario: str) -> float:
        """
        Returns the carbon price for the given year and scenario
        from self.carbon_price_data.
        """
        row = self.carbon_price_data.loc[self.carbon_price_data['year'] == year, scenario]
        if row.empty:
            raise ValueError(f"No carbon price for year={year}, scenario={scenario}")
        return float(row.values[0])

    def get_allow_rate(self, year: int) -> float:
        """
        Returns the fraction (0.15 for 15%) from the allowance_rate_data
        for the given year, from a column 'allow_rate'.
        """
        row = self.allowance_rate_data.loc[self.allowance_rate_data['year'] == year, 'allow_rate']
        if row.empty:
            raise ValueError(f"No allowance rate for year={year}")
        return float(row.values[0])

    def get_emission_intensity(self, year: int, tech: str) -> float:
        """
        Returns the emission intensity for a given (year, tech).
        """
        row = self.tech_emission_data.loc[self.tech_emission_data['year'] == year, tech]
        if row.empty:
            raise ValueError(f"No emission intensity for year={year}, tech={tech}")
        return float(row.values[0])

    def get_mac(self, year: int, tech: str) -> float:
        """
        Returns the marginal abatement cost (MAC) for a given (year, tech).
        """
        row = self.tech_mac_data.loc[self.tech_mac_data['year'] == year, tech]
        if row.empty:
            raise ValueError(f"No MAC data for year={year}, tech={tech}")
        return float(row.values[0])
