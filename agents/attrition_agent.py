from __future__ import annotations
import numpy as np
from .base_agent import BaseAgent


class AttritionAgent(BaseAgent):
    name = "Attrition Agent"

    def __init__(self, rng=None):
        self.rng = rng or np.random.default_rng(11)

    def _risk_score(self, emp, bench_days):
        score = 0
        if bench_days and bench_days > 30:
            score += 25
        if bench_days and bench_days > 60:
            score += 15
        if emp.get("last_rating", 3) is not None and emp.get("last_rating", 3) <= 2.5:
            score += 15
        tenure_days = emp.get("tenure_days", 9999)
        if tenure_days is not None and tenure_days <= 180:
            score += 10
        return score

    def decide(self, state):
        actions = []
        today = state.sim_date
        for emp_id, emp in state.active_employees().iterrows():
            bench_start = emp.get("bench_start_date")
            bench_days = (today - bench_start).days if isinstance(bench_start, type(today)) else 0
            score = self._risk_score(emp, bench_days)
            state.employees.loc[emp_id, "attrition_risk_score"] = score
            state.employees.loc[emp_id, "risk_category"] = (
                "High Risk" if score >= 40 else "Medium Risk" if score >= 20 else "Low Risk"
            )
            exit_probability = min(score / 3500, 0.012)
            if self.rng.random() < exit_probability:
                actions.append({
                    "action_type": "EXIT_EMPLOYEE",
                    "entity_type": "employee",
                    "entity_id": emp_id,
                    "business_reason": f"Attrition risk score {score} (bench {bench_days}d, rating {emp.get('last_rating')})",
                    "confidence_score": score,
                })
        return actions

    def act(self, state, actions):
        for a in actions:
            emp_id = a["entity_id"]
            state.employees.loc[emp_id, "employment_status"] = "Exited"
            state.employees.loc[emp_id, "exit_date"] = state.sim_date
            state.employees.loc[emp_id, "deployment_status"] = "Exited"
            state.log_event("EMPLOYEE_EXITED", employee_id=emp_id,
                             old_state="Active", new_state="Exited",
                             reason=a["business_reason"], agent=self.name)