from __future__ import annotations


class InsightAgent:
    name = "Insight Agent"

    def summarize(self, kpi_row):
        parts = [f"{kpi_row['date']}:"]
        if kpi_row["exits_today"]:
            parts.append(f"{kpi_row['exits_today']} employee(s) exited.")
        if kpi_row["deployments_today"]:
            parts.append(f"{kpi_row['deployments_today']} bench employee(s) deployed to customers.")
        if kpi_row["rotations_today"]:
            parts.append(f"{kpi_row['rotations_today']} employee(s) rotated off long-running accounts.")
        if kpi_row["reallocations_today"]:
            parts.append(f"Budget reallocated for {kpi_row['reallocations_today']} at-risk customer(s).")
        if kpi_row["bench_30plus"] > 0:
            parts.append(f"{kpi_row['bench_30plus']} people are on the bench 30+ days.")
        if len(parts) == 1:
            parts.append("Steady day -- no material staffing or budget changes.")
        return " ".join(parts)