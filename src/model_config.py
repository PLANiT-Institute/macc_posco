# src/model_config.py

class ModelConfig:
    """
    Stores model-wide configuration:
      - start_year, end_year
      - discount_rate
      - scenarios
      - path to results directory
    """

    def __init__(
        self,
        start_year=2024,
        end_year=2050,
        discount_rate=0.05,
        scenarios=None,
        results_dir="results2_posco"
    ):
        if scenarios is None:
            scenarios = ['below_2', 'ndc', 'net_zero']

        self.start_year = start_year
        self.end_year = end_year
        self.discount_rate = discount_rate
        self.scenarios = scenarios
        self.results_dir = results_dir

    def __repr__(self):
        return (
            f"ModelConfig(start_year={self.start_year}, end_year={self.end_year}, "
            f"discount_rate={self.discount_rate}, scenarios={self.scenarios}, "
            f"results_dir='{self.results_dir}')"
        )
