import pandas as pd

# --- Step 1: some pretend data, just 5 employees, to keep this simple ---
employees = pd.DataFrame({
    "employee_id": ["E1", "E2", "E3", "E4", "E5"],
    "bench_days": [5, 45, 12, 70, 0],
    "skill": ["Data Science", "Data Science", "QA", "Backend", "QA"],
})

print("BEFORE:")
print(employees)


# --- Step 2: the agent's "decide" step ---
def decide_who_is_at_risk(employees_df):
    """Look at each employee's bench_days and decide who counts as at-risk.
    Returns a list of decisions, each with a stated reason."""
    decisions = []
    for _, row in employees_df.iterrows():
        if row["bench_days"] > 30:
            decisions.append({
                "employee_id": row["employee_id"],
                "reason": f"On the bench for {row['bench_days']} days, over the 30-day threshold"
            })
    return decisions


# --- Step 3: the agent's "act" step ---
def mark_as_at_risk(employees_df, decisions):
    """Apply the decisions: add a new column marking who's at risk."""
    at_risk_ids = [d["employee_id"] for d in decisions]
    employees_df["at_risk"] = employees_df["employee_id"].isin(at_risk_ids)


# --- Run the agent: perceive (we already loaded the data) -> decide -> act ---
decisions = decide_who_is_at_risk(employees)
mark_as_at_risk(employees, decisions)

print("\nDECISIONS MADE:")
for d in decisions:
    print(f"  {d['employee_id']}: {d['reason']}")

print("\nAFTER:")
print(employees)