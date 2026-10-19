import pandas as pd

# Load the two files we need for this step
employees = pd.read_csv("data/employees.csv")
assignments = pd.read_csv("data/assignments.csv")

# Print the first 5 rows of each, so we can see what we're working with
print(employees.head())
print(assignments.head())

# A "billable" assignment is one where the customer is actually being charged
assignments["is_billable"] = assignments["billing_rate"] > 0

print(assignments[["employee_id", "billing_rate", "is_billable"]].head(10))

'''Calculate tenure in days'''

# Convert the date columns from plain text into real dates Python can do math on
employees["hire_date"] = pd.to_datetime(employees["hire_date"])
employees["exit_date"] = pd.to_datetime(employees["exit_date"])

# "today" for this calculation
today = pd.Timestamp.today().normalize()

# For people still employed (exit_date is blank), use today's date to measure tenure so far.
# For people who left, use their actual exit date.
employees["end_reference_date"] = employees["exit_date"].fillna(today)
employees["tenure_days"] = (employees["end_reference_date"] - employees["hire_date"]).dt.days

print(employees[["employee_id", "hire_date", "exit_date", "tenure_days"]].head(10))

'''Build a simple attrition risk score'''

# Start everyone at 0 risk points
employees["attrition_risk_score"] = 0

# Add points for low performance ratings
employees.loc[employees["last_rating"] <= 2.5, "attrition_risk_score"] += 15

# Add points for short tenure (people are more likely to leave early on)
employees.loc[employees["tenure_days"] <= 180, "attrition_risk_score"] += 10

# Turn the score into a readable category
def categorize(score):
    if score >= 40:
        return "High Risk"
    elif score >= 20:
        return "Medium Risk"
    else:
        return "Low Risk"

employees["risk_category"] = employees["attrition_risk_score"].apply(categorize)

print(employees[["employee_id", "attrition_risk_score", "risk_category"]].head(10))

employees.to_csv("data/employee_features.csv", index=False)
print("Saved employee_features.csv")