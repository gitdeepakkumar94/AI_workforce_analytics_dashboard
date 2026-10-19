import json
import pandas as pd

kpis = pd.read_csv("data/processed/daily_org_kpis.csv")
events = pd.read_csv("data/processed/workforce_events.csv")
emp = pd.read_csv("data/processed/employees_final_state.csv")

# Most recent 50 events, newest first
feed = events.sort_values("event_date", ascending=False).head(50)
feed_records = feed[["event_date", "event_type", "employee_id", "reason", "created_by_agent"]].fillna("").to_dict("records")

active = emp[emp["employment_status"] == "Active"]
risk_dist = active["risk_category"].value_counts().to_dict()
deployment_dist = active["deployment_status"].value_counts().to_dict()
skill_dist = active["skill"].value_counts().to_dict()

data = {
    "kpi_daily": kpis.to_dict("records"),
    "feed": feed_records,
    "risk_dist": risk_dist,
    "deployment_dist": deployment_dist,
    "skill_dist": skill_dist,
    "meta": {
        "sim_start": kpis["date"].min(),
        "sim_end": kpis["date"].max(),
        "starting_headcount": int(kpis.iloc[0]["active_headcount"]),
        "ending_headcount": int(kpis.iloc[-1]["active_headcount"]),
        "total_events": int(len(events)),
    },
}

with open("dashboard_data.json", "w") as f:
    json.dump(data, f)

print("Wrote dashboard_data.json")