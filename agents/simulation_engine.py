from __future__ import annotations
import numpy as np
import pandas as pd


class WorkforceState:
    """Holds everything about 'today': who's employed, who's assigned where,
    what demand is open, and every log of what happened so far."""

    def __init__(self, employees, customers, projects, assignments, budgets, sim_start):
        self.employees = employees.set_index("employee_id", drop=False)
        self.customers = customers.set_index("customer_id", drop=False)
        self.projects = projects.set_index("project_id", drop=False)
        self.assignments = assignments.copy()
        self.budgets = budgets.copy()

        self.sim_date = sim_start
        self.counter = 90000
        self.demand_requests = []
        self.events = []
        self.actions = []

    def log_event(self, event_type, employee_id=None, customer_id=None,
                  project_id=None, old_state=None, new_state=None,
                  reason="", agent="SimulationEngine"):
        self.counter += 1
        self.events.append({
            "event_id": f"EVT{self.counter}",
            "event_date": self.sim_date.date().isoformat(),
            "event_type": event_type,
            "employee_id": employee_id,
            "customer_id": customer_id,
            "project_id": project_id,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "created_by_agent": agent,
        })

    def log_actions(self, agent_name, actions):
        for a in actions:
            self.counter += 1
            row = {"action_id": f"ACT{self.counter}", "action_date": self.sim_date.date().isoformat(),
                   "agent_name": agent_name}
            row.update({k: v for k, v in a.items() if k not in row})
            self.actions.append(row)

    def active_employees(self):
        return self.employees[self.employees["employment_status"] == "Active"]

    def bench_employees(self):
        e = self.active_employees()
        return e[e["deployment_status"] == "Bench"]


class DemandAgent:
    """Invents new customer staffing requests, roughly scaled to how many
    people are currently on the bench (so demand can realistically clear it)."""
    name = "Demand Agent"

    def __init__(self, daily_demand_prob=0.55, rng=None):
        self.daily_demand_prob = daily_demand_prob
        self.rng = rng or np.random.default_rng(7)

    def run(self, state):
        actions = []
        bench_pool = state.bench_employees()
        n_target = max(1, int(len(bench_pool) * 0.06))
        if self.rng.random() < self.daily_demand_prob:
            n_new = self.rng.integers(1, n_target + 2)
            customers = state.customers.sample(n=min(n_new, len(state.customers)))
            bench_skills = bench_pool["skill"].dropna()
            skills = bench_skills if len(bench_skills) else state.employees["skill"].dropna()
            for _, cust in customers.iterrows():
                cust_projects = state.projects[state.projects["customer_id"] == cust["customer_id"]]
                project_id = cust_projects["project_id"].sample(1).iloc[0] if len(cust_projects) else None
                skill = self.rng.choice(skills.values if hasattr(skills, "values") else skills)
                demand = {
                    "demand_id": f"DEM{state.counter}",
                    "request_date": state.sim_date.date().isoformat(),
                    "customer_id": cust["customer_id"],
                    "project_id": project_id,
                    "required_skill": skill,
                    "status": "Open",
                }
                state.counter += 1
                state.demand_requests.append(demand)
                actions.append({
                    "action_type": "DEMAND_OPENED",
                    "entity_type": "demand",
                    "entity_id": demand["demand_id"],
                    "business_reason": f"{cust['customer_name']} requested a {skill} resource",
                })
        if actions:
            state.log_actions(self.name, actions)
        return actions


class AssignmentLifecycleAgent:
    """Closes assignments whose end date has arrived and puts that employee
    on the bench. This one is deterministic bookkeeping, not a 'decision.'"""
    name = "Assignment Lifecycle"

    def run(self, state):
        today = state.sim_date
        a = state.assignments
        ending_today = a[(a["status"] == "Active") & (a["assignment_end_date"] == today)]
        for _, row in ending_today.iterrows():
            emp_id = row["employee_id"]
            if emp_id not in state.employees.index:
                continue
            state.assignments.loc[state.assignments["assignment_id"] == row["assignment_id"], "status"] = "Closed"
            state.employees.loc[emp_id, "deployment_status"] = "Bench"
            state.employees.loc[emp_id, "current_customer_id"] = np.nan
            state.employees.loc[emp_id, "current_project_id"] = np.nan
            state.employees.loc[emp_id, "bench_start_date"] = today
            state.log_event("ASSIGNMENT_ENDED", employee_id=emp_id, customer_id=row["customer_id"],
                             project_id=row["project_id"], old_state="Deployed", new_state="Bench",
                             reason="Assignment reached its end date")