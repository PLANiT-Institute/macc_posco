# src/optimizer.py

import pulp

class Optimizer:
    """
    Class-based optimizer to solve the steel transition with:
      - one tech per facility-year
      - forced H2 after end-year
      - allowance offset in the objective
      - no multi-year lock in
    """

    def __init__(self, data_manager, model_config):
        self.dm = data_manager
        self.config = model_config

        # We'll define the technologies in a fixed list, matching columns in the data
        self.technologies = ["BF_BOF", "BF_BOF_scrap", "BF_BOF_CCUS", "H2_HDRI_EAF"]

    def solve_for_scenarios(self):
        """
        Build one PuLP problem, re-set the objective for each scenario,
        solve, store results. Return a dict: results[scenario] = ...
        """
        results = {}

        # 1) Create a single problem
        self.prob = pulp.LpProblem("Emission_Path_Optimization", pulp.LpMinimize)

        # We'll define variables and *permanent* constraints once,
        # then only swap out the objective for each scenario.

        facility_df = self.dm.facility_data
        start_y = self.config.start_year
        end_y = self.config.end_year

        num_facilities = len(facility_df)
        num_techs = len(self.technologies)

        # =========== Decision Variables ============
        # x[i, t, y] ∈ {0,1}
        self.x = pulp.LpVariable.dicts(
            "tech_choice",
            ((i, t, y) for i in range(num_facilities)
                       for t in range(num_techs)
                       for y in range(start_y, end_y + 1)),
            cat=pulp.LpBinary
        )

        # =========== Constraints ============

        # A) One tech per facility-year
        for i in range(num_facilities):
            for y in range(start_y, end_y + 1):
                self.prob += pulp.lpSum(self.x[i, t, y] for t in range(num_techs)) == 1

        # B) Force H2 after end_year
        #    We'll assume the column is 'end_year' in facility_data.
        #    If it's 'end-year', adjust accordingly.
        for i in range(num_facilities):
            facility_end = int(facility_df.loc[i, 'end_year'])
            if facility_end <= end_y:
                # For y in [facility_end..end_y], x[i, H2_idx, y] = 1
                h2_idx = 3  # H2_HDRI_EAF
                for y in range(facility_end, end_y + 1):
                    self.prob += self.x[i, h2_idx, y] == 1
                    # And other technologies = 0
                    for t in range(num_techs):
                        if t != h2_idx:
                            self.prob += self.x[i, t, y] == 0

        # Now we can solve each scenario with a different objective
        for scenario in self.config.scenarios:
            # Build the objective expression for the scenario
            cost_expr = []
            for i in range(num_facilities):
                cap_i = facility_df.loc[i, 'capacity']
                for y in range(start_y, end_y + 1):
                    # discount factor
                    discount_factor = 1.0 / ((1.0 + self.config.discount_rate) ** (y - start_y))

                    for t_idx, tech_name in enumerate(self.technologies):
                        carbon_p = self.dm.get_carbon_price(y, scenario)
                        emi_int = self.dm.get_emission_intensity(y, tech_name)
                        allow_fraction = self.dm.get_allow_rate(y)
                        # Carbon cost
                        carbon_cost = cap_i * emi_int * carbon_p
                        # Allowance offset
                        allowance_offset = carbon_cost * allow_fraction
                        # Abatement cost
                        bf_bof_int = self.dm.get_emission_intensity(y, "BF_BOF")
                        mac_val = self.dm.get_mac(y, tech_name)
                        abatement = cap_i * (bf_bof_int - emi_int) * mac_val

                        total_cost = (carbon_cost - allowance_offset + abatement) * discount_factor
                        cost_expr.append(self.x[i, t_idx, y] * total_cost)

            # Set objective and solve
            self.prob.setObjective(pulp.lpSum(cost_expr))
            self.prob.solve(pulp.PULP_CBC_CMD(msg=0))

            status = pulp.LpStatus[self.prob.status]
            objective_value = pulp.value(self.prob.objective)

            # Collect decisions
            decisions = {}
            for i in range(num_facilities):
                for y in range(start_y, end_y + 1):
                    chosen_tech = None
                    for t_idx in range(num_techs):
                        if pulp.value(self.x[i, t_idx, y]) == 1:
                            chosen_tech = self.technologies[t_idx]
                            break
                    decisions[(i, y)] = chosen_tech

            results[scenario] = {
                'status': status,
                'objective_value': objective_value,
                'decisions': decisions
            }

        return results
