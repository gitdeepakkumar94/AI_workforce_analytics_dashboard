from __future__ import annotations
import pandas as pd
from .base_agent import BaseAgent


class DeploymentAgent(BaseAgent):
    name = "Deployment Agent"

    def _score(self, emp, today):
        score = 0
        bench_start = emp.get("bench_start_date")
        bench_days = (today - bench_start).days if isinstance(bench_start, type(today)) else 0
        if bench_days > 30:
            score += 25
        if bench_days > 60:
            score += 15
        if (emp.get("last_rating") or 0) >= 4:
            score += 10
        return score, bench_days

    def decide(self, state):
        actions = []
        bench = state.bench_employees()
        for demand in state.demand_requests:
            if demand["status"] != "Open":
                continue
            candidates = bench[bench["skill"] == demand["required_skill"]]
            if len(candidates) == 0:
                continue
            scored = [(emp_id, *self._score(emp, state.sim_date)) for emp_id, emp in candidates.iterrows()]
            scored.sort(key=lambda x: x[1], reverse=True)
            best_emp_id, best_score, bench_days = scored[0]
            actions.append({
                "action_type": "DEPLOY_EMPLOYEE",
                "entity_type": "employee",
                "entity_id": best_emp_id,
                "demand_id": demand["demand_id"],
                "customer_id": demand["customer_id"],
                "project_id": demand["project_id"],
                "business_reason": f"Skill match on {demand['required_skill']}, {bench_days}d on bench",
                "confidence_score": best_score,
            })
            bench = bench.drop(index=best_emp_id)
            demand["status"] = "Filled"
        state.demand_requests = [d for d in state.demand_requests if d["status"] == "Open"]
        return actions

    def act(self, state, actions):
        for a in actions:
            emp_id = a["entity_id"]
            new_id = self._new_id("ASGN", state)
            new_row = {
                "assignment_id": new_id, "employee_id": emp_id,
                "customer_id": a["customer_id"], "project_id": a["project_id"],
                "assignment_start_date": state.sim_date,
                "assignment_end_date": state.sim_date + pd.Timedelta(days=120),
                "allocation_percent": 100, "billing_rate": 120.0, "cost_rate": 70.0,
                "status": "Active",
            }
            state.assignments = pd.concat([state.assignments, pd.DataFrame([new_row])], ignore_index=True)
            state.employees.loc[emp_id, "deployment_status"] = "Deployed"
            state.employees.loc[emp_id, "current_customer_id"] = a["customer_id"]
            state.employees.loc[emp_id, "current_project_id"] = a["project_id"]
            state.employees.loc[emp_id, "bench_start_date"] = pd.NaT
            state.log_event("DEPLOYMENT_ASSIGNED", employee_id=emp_id, customer_id=a["customer_id"],
                             project_id=a["project_id"], old_state="Bench", new_state="Deployed",
                             reason=a["business_reason"], agent=self.name)