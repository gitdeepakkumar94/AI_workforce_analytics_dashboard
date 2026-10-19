from __future__ import annotations
import pandas as pd
from .base_agent import BaseAgent


class BudgetAgent(BaseAgent):
    name = "Budget Agent"

    def __init__(self):
        self._reallocated_months = set()

    def _month_key(self, date):
        return pd.Timestamp(date.year, date.month, 1)

    def accrue(self, state):
        """Runs every day: adds today's spend onto the right budget row."""
        month = self._month_key(state.sim_date)
        active = state.assignments[(state.assignments["status"] == "Active") &
                                    (state.assignments["billing_rate"] > 0)]
        for _, row in active.iterrows():
            if pd.isna(row["customer_id"]) or pd.isna(row["project_id"]):
                continue
            daily_spend = float(row["billing_rate"]) * (float(row["allocation_percent"]) / 100.0)
            mask = (
                (state.budgets["customer_id"] == row["customer_id"]) &
                (state.budgets["project_id"] == row["project_id"]) &
                (state.budgets["budget_month"] == month)
            )
            if mask.any():
                state.budgets.loc[mask, "actual_amount"] += daily_spend
            else:
                hist = state.budgets[state.budgets["customer_id"] == row["customer_id"]]
                default_budget = hist["budget_amount"].mean() if len(hist) else 20000.0
                state.budgets = pd.concat([state.budgets, pd.DataFrame([{
                    "budget_id": f"BUDSIM{state.counter}", "customer_id": row["customer_id"],
                    "project_id": row["project_id"], "budget_month": month,
                    "budget_amount": default_budget, "actual_amount": daily_spend,
                    "budget_hours": 0, "actual_hours": 0,
                }])], ignore_index=True)
                state.counter += 1

    def decide(self, state):
        actions = []
        if state.sim_date.day != 1:
            return actions
        month = self._month_key(state.sim_date)
        if month in self._reallocated_months:
            return actions
        month_budgets = state.budgets[state.budgets["budget_month"] == month]
        by_customer = month_budgets.groupby("customer_id").agg(
            budget=("budget_amount", "sum"), actual=("actual_amount", "sum")
        ).reset_index()
        if by_customer.empty:
            return actions
        by_customer["burn_rate"] = by_customer["actual"] / by_customer["budget"].replace(0, pd.NA)
        high = by_customer[by_customer["burn_rate"] > 0.9].sort_values("burn_rate", ascending=False)
        low = by_customer[by_customer["burn_rate"] < 0.6].sort_values("burn_rate")
        for i, hrow in enumerate(high.itertuples()):
            if i >= len(low):
                break
            lrow = low.iloc[i]
            amount = round(min(hrow.budget * 0.1, lrow["budget"] * 0.2), 2)
            if amount <= 0:
                continue
            actions.append({
                "action_type": "REALLOCATE_BUDGET", "entity_type": "customer",
                "entity_id": hrow.customer_id, "from_customer_id": lrow["customer_id"],
                "to_customer_id": hrow.customer_id, "amount": amount, "month": month.date().isoformat(),
                "business_reason": f"Burn rate {hrow.burn_rate:.0%} vs donor at {lrow['burn_rate']:.0%}",
                "confidence_score": round(hrow.burn_rate, 2),
            })
        self._reallocated_months.add(month)
        return actions

    def act(self, state, actions):
        for a in actions:
            month = pd.Timestamp(a["month"])
            to_mask = (state.budgets["customer_id"] == a["to_customer_id"]) & (state.budgets["budget_month"] == month)
            from_mask = (state.budgets["customer_id"] == a["from_customer_id"]) & (state.budgets["budget_month"] == month)
            if to_mask.any():
                state.budgets.loc[to_mask, "budget_amount"] += a["amount"] / to_mask.sum()
            if from_mask.any():
                state.budgets.loc[from_mask, "budget_amount"] -= a["amount"] / from_mask.sum()
            state.log_event("BUDGET_REALLOCATED", customer_id=a["to_customer_id"],
                             old_state=a["from_customer_id"], new_state=a["to_customer_id"],
                             reason=a["business_reason"], agent=self.name)