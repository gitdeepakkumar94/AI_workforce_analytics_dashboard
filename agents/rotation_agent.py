from __future__ import annotations
import numpy as np
from .base_agent import BaseAgent


class RotationAgent(BaseAgent):
    name = "Rotation Agent"

    def __init__(self, rng=None):
        self.rng = rng or np.random.default_rng(23)

    def decide(self, state):
        actions = []
        today = state.sim_date
        active_asgn = state.assignments[state.assignments["status"] == "Active"]
        for _, row in active_asgn.iterrows():
            days_in_role = (today - row["assignment_start_date"]).days
            if days_in_role < 180:
                continue
            prob = 0.01 if days_in_role < 365 else 0.03
            if self.rng.random() < prob:
                actions.append({
                    "action_type": "ROTATE_EMPLOYEE", "entity_type": "employee",
                    "entity_id": row["employee_id"], "assignment_id": row["assignment_id"],
                    "customer_id": row["customer_id"], "project_id": row["project_id"],
                    "business_reason": f"{days_in_role}d on the same account without rotation",
                })
        return actions

    def act(self, state, actions):
        for a in actions:
            emp_id = a["entity_id"]
            if emp_id not in state.employees.index or state.employees.loc[emp_id, "employment_status"] != "Active":
                continue
            state.assignments.loc[state.assignments["assignment_id"] == a["assignment_id"], "status"] = "Closed"
            state.employees.loc[emp_id, "deployment_status"] = "Bench"
            state.employees.loc[emp_id, "current_customer_id"] = None
            state.employees.loc[emp_id, "current_project_id"] = None
            state.employees.loc[emp_id, "bench_start_date"] = state.sim_date

            skill = state.employees.loc[emp_id, "skill"]
            # IMPORTANT: always pick a real, different customer here -- never leave this as None.
            # (see the "bug I hit" box below for why)
            other_customers = state.customers[state.customers["customer_id"] != a["customer_id"]]
            new_cust = other_customers.sample(1).iloc[0] if len(other_customers) else None
            new_project_id = None
            if new_cust is not None:
                cust_projects = state.projects[state.projects["customer_id"] == new_cust["customer_id"]]
                if len(cust_projects):
                    new_project_id = cust_projects["project_id"].sample(1).iloc[0]

            state.counter += 1
            state.demand_requests.append({
                "demand_id": f"DEM{state.counter}",
                "request_date": state.sim_date.date().isoformat(),
                "customer_id": new_cust["customer_id"] if new_cust is not None else None,
                "project_id": new_project_id, "required_skill": skill, "status": "Open",
            })
            state.log_event("ROTATION_INITIATED", employee_id=emp_id, customer_id=a["customer_id"],
                             project_id=a["project_id"], old_state="Deployed", new_state="Bench",
                             reason=a["business_reason"], agent=self.name)