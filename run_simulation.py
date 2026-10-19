import argparse
import numpy as np
import pandas as pd

from agents.simulation_engine import WorkforceState, DemandAgent, AssignmentLifecycleAgent
from agents.attrition_agent import AttritionAgent
from agents.deployment_agent import DeploymentAgent
from agents.rotation_agent import RotationAgent
from agents.budget_agent import BudgetAgent
from agents.insight_agent import InsightAgent

DATA = "data"
OUT = "data/processed"


def load_data():
    employees = pd.read_csv(f"{DATA}/employees.csv")
    customers = pd.read_csv(f"{DATA}/customers.csv")
    projects = pd.read_csv(f"{DATA}/projects.csv")
    assignments = pd.read_csv(f"{DATA}/assignments.csv")
    budgets = pd.read_csv(f"{DATA}/budgets.csv")

    employees["hire_date"] = pd.to_datetime(employees["hire_date"])
    employees["exit_date"] = pd.to_datetime(employees["exit_date"])
    assignments["assignment_start_date"] = pd.to_datetime(assignments["assignment_start_date"], dayfirst=True)
    assignments["assignment_end_date"] = pd.to_datetime(assignments["assignment_end_date"], dayfirst=True)
    budgets["budget_month"] = pd.to_datetime(budgets["budget_month"])
    return employees, customers, projects, assignments, budgets


def seed_state(employees, customers, projects, assignments, budgets, sim_start):
    """Turn your historical CSVs into a realistic 'as of today' starting point:
    who's currently deployed, who's on the bench, and for how long."""
    assignments = assignments.copy()
    assignments["status"] = np.where(
        (assignments["assignment_start_date"] <= sim_start) &
        (assignments["assignment_end_date"] >= sim_start),
        "Active", "Closed"
    )

    employees = employees.copy()
    employees["deployment_status"] = "Bench"
    employees["current_customer_id"] = None
    employees["current_project_id"] = None
    employees["bench_start_date"] = pd.NaT
    employees["attrition_risk_score"] = 0
    employees["risk_category"] = "Low Risk"
    employees["tenure_days"] = (sim_start - employees["hire_date"]).dt.days

    active_asgn = assignments[assignments["status"] == "Active"]
    latest_active = active_asgn.sort_values("assignment_end_date").drop_duplicates("employee_id", keep="last")
    employees = employees.set_index("employee_id", drop=False)
    for _, row in latest_active.iterrows():
        emp_id = row["employee_id"]
        if emp_id in employees.index:
            employees.loc[emp_id, "deployment_status"] = "Deployed"
            employees.loc[emp_id, "current_customer_id"] = row["customer_id"]
            employees.loc[emp_id, "current_project_id"] = row["project_id"]
    employees = employees.reset_index(drop=True)

    # For people on the bench, "how long" is measured from their last closed
    # assignment -- clipped to 45 days back, since sparse historical data would
    # otherwise make almost everyone look like a years-long bench case on day 1.
    past = assignments[assignments["assignment_end_date"] < sim_start]
    last_end = past.sort_values("assignment_end_date").groupby("employee_id")["assignment_end_date"].last()
    lookback_floor = sim_start - pd.Timedelta(days=45)
    employees = employees.set_index("employee_id", drop=False)
    for emp_id in employees.index:
        if employees.loc[emp_id, "deployment_status"] == "Bench":
            candidate = last_end.get(emp_id, employees.loc[emp_id, "hire_date"])
            employees.loc[emp_id, "bench_start_date"] = max(candidate, lookback_floor)
    employees = employees.reset_index(drop=True)

    exited_mask = employees["exit_date"].notna() & (employees["exit_date"] <= sim_start)
    employees.loc[exited_mask, "employment_status"] = "Exited"
    employees.loc[exited_mask, "deployment_status"] = "Exited"

    return WorkforceState(employees, customers, projects, assignments, budgets, sim_start)


def snapshot_org_kpis(state, events_today):
    active = state.active_employees()
    bench = active[active["deployment_status"] == "Bench"]
    bench_days = (state.sim_date - bench["bench_start_date"]).dt.days.fillna(0)

    month = pd.Timestamp(state.sim_date.year, state.sim_date.month, 1)
    month_budget = state.budgets[state.budgets["budget_month"] == month]
    total_budget = float(month_budget["budget_amount"].sum())
    total_actual = float(month_budget["actual_amount"].sum())

    return {
        "date": state.sim_date.date().isoformat(),
        "active_headcount": int(len(active)),
        "exits_today": sum(1 for e in events_today if e["event_type"] == "EMPLOYEE_EXITED"),
        "deployed_count": int((active["deployment_status"] == "Deployed").sum()),
        "bench_count": int((active["deployment_status"] == "Bench").sum()),
        "bench_30plus": int((bench_days > 30).sum()),
        "deployments_today": sum(1 for e in events_today if e["event_type"] == "DEPLOYMENT_ASSIGNED"),
        "rotations_today": sum(1 for e in events_today if e["event_type"] == "ROTATION_INITIATED"),
        "reallocations_today": sum(1 for e in events_today if e["event_type"] == "BUDGET_REALLOCATED"),
        "high_risk_count": int((active["risk_category"] == "High Risk").sum()),
        "avg_risk_score": round(float(active["attrition_risk_score"].mean() or 0), 1),
        "org_burn_rate": round(total_actual / total_budget, 4) if total_budget else 0,
    }


def main(n_days, sim_start):
    employees, customers, projects, assignments, budgets = load_data()
    sim_start = pd.Timestamp(sim_start)
    state = seed_state(employees, customers, projects, assignments, budgets, sim_start)

    demand_agent = DemandAgent()
    lifecycle_agent = AssignmentLifecycleAgent()
    attrition_agent = AttritionAgent()
    deployment_agent = DeploymentAgent()
    rotation_agent = RotationAgent()
    budget_agent = BudgetAgent()
    insight_agent = InsightAgent()

    daily_kpis = []
    daily_summaries = []

    for day_offset in range(n_days):
        state.sim_date = sim_start + pd.Timedelta(days=day_offset)
        events_before = len(state.events)

        lifecycle_agent.run(state)
        demand_agent.run(state)
        attrition_agent.run(state)
        rotation_agent.run(state)
        deployment_agent.run(state)
        budget_agent.accrue(state)
        budget_agent.run(state)

        events_today = state.events[events_before:]
        kpi_row = snapshot_org_kpis(state, events_today)
        daily_kpis.append(kpi_row)
        daily_summaries.append({"date": kpi_row["date"], "summary": insight_agent.summarize(kpi_row)})

    pd.DataFrame(daily_kpis).to_csv(f"{OUT}/daily_org_kpis.csv", index=False)
    pd.DataFrame(state.events).to_csv(f"{OUT}/workforce_events.csv", index=False)
    pd.DataFrame(state.actions).to_csv(f"{OUT}/agent_actions.csv", index=False)
    pd.DataFrame(daily_summaries).to_csv(f"{OUT}/daily_insight_log.csv", index=False)
    state.employees.reset_index(drop=True).to_csv(f"{OUT}/employees_final_state.csv", index=False)

    print(f"Simulated {n_days} days from {sim_start.date()}.")
    print(f"Events logged: {len(state.events)} | Agent actions logged: {len(state.actions)}")
    print(pd.DataFrame(daily_kpis).tail(5).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--start", type=str, default=pd.Timestamp.today().normalize().date().isoformat())
    args = parser.parse_args()
    main(args.days, args.start)