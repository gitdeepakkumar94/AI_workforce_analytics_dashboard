# AI Workforce Analytics Dashboard

A Python workforce simulation that uses cooperating agents to model employee deployment, bench time, attrition, account rotation, and budget allocation. A browser dashboard turns the simulation results into workforce metrics, trend charts, and an activity feed.

The agents use business rules and simulated events. No external AI API, API key, or trained machine learning model is required.

## Features

- Track active headcount, deployed employees, bench employees, and high-risk employees.
- Score attrition risk using bench duration, performance ratings, and tenure.
- Match available employees to customer demand by skill and deployment priority.
- Simulate assignment completions, employee exits, and account rotations.
- Accrue assignment spending and evaluate monthly budget reallocations.
- Export daily KPIs, agent actions, workforce events, and plain-language summaries.
- View deployment and attrition-risk trends in a static HTML dashboard.

## How it works

```text
CSV inputs in data/
        |
        v
run_simulation.py
        |
        v
Simulation outputs in data/processed/
        |
        v
build_dashboard_data.py -> dashboard_data.json
        |
        v
assemble_dashboard.py + dashboard_template.html
        |
        v
workforce_dashboard.html
```

Each simulated day processes assignment completions, customer demand, attrition, rotations, deployment, and budgets. It then records organization metrics and a daily summary.

| Agent | Responsibility |
| --- | --- |
| Assignment Lifecycle | Close assignments that end that day and return employees to the bench. |
| Demand Agent | Generate simulated customer staffing requests. |
| Attrition Agent | Calculate risk scores and simulate employee exits. |
| Rotation Agent | Rotate employees from long-running assignments and create replacement demand. |
| Deployment Agent | Assign available employees to requests with matching skills. |
| Budget Agent | Accrue spending and evaluate reallocations between customers. |
| Insight Agent | Produce a text summary of the day's workforce changes. |

## Technology

- **Python**, **pandas**, and **NumPy** for data preparation and simulation.
- **HTML**, **CSS**, **JavaScript**, and **Chart.js** for the dashboard.
- **SQLite / SQL** for the separate database and analysis queries included in the repository.

The simulation and dashboard pipeline reads CSV files directly; it does not require a database server.

## Getting started

### 1. Clone the project branch

```bash
git clone --branch workforce_project https://github.com/gitdeepakkumar94/AI_workforce_analytics_dashboard.git
cd AI_workforce_analytics_dashboard
```

If you already have the project locally, open a terminal in its root folder instead.

### 2. Set up Python dependencies

Install Python 3, then create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install pandas numpy
```

On Windows, use `python` in place of `python3` when creating the environment if that is your Python command.

### 3. Run the simulation and build the dashboard

Run these commands from the project root:

```bash
python run_simulation.py --days 90 --start 2026-09-27
python build_dashboard_data.py
python assemble_dashboard.py
```

`--days` sets the number of days to simulate. `--start` sets the starting date in `YYYY-MM-DD` format. If omitted, the defaults are 60 days and the current date. The explicit date above matches the start of the results included in the repository.

Each run replaces the generated CSV outputs and, after the build steps, the dashboard data and HTML file. The source CSV inputs remain unchanged.

### 4. View the dashboard

Open `workforce_dashboard.html` in a web browser. Keep `chart.min.js` in the same folder so the charts can load. Simulation data is embedded in the generated HTML, so a backend server is not required.

You can also view the included dashboard before running Python. GitHub's file view displays HTML source; clone or download the project to open the dashboard locally.

## Project structure

```text
AI_workforce_analytics_dashboard/
├── agents/                      # Agent implementations and shared simulation state
├── data/
│   ├── employees.csv            # Employee attributes and employment history
│   ├── customers.csv            # Customer information
│   ├── projects.csv             # Customer projects
│   ├── assignments.csv          # Employee assignment history
│   ├── budgets.csv              # Monthly project budgets and spending
│   ├── bench_history.csv        # Additional data for analysis
│   ├── employee_features.csv    # Output of the optional cleaning script
│   └── processed/               # Generated simulation results
├── sql/
│   └── sql_queries.sql          # Workforce data quality and analysis queries
├── run_simulation.py            # Simulation entry point
├── build_dashboard_data.py      # Convert simulation outputs to dashboard JSON
├── assemble_dashboard.py        # Embed JSON in the dashboard template
├── dashboard_template.html     # Dashboard layout and chart code
├── dashboard_data.json          # Generated dashboard data
├── workforce_dashboard.html     # Generated browser dashboard
├── chart.min.js                 # Local Chart.js dependency
├── clean_data.py                # Optional employee feature preparation
├── mini_agent_demo.py           # Small standalone agent example
├── workforce.db                 # Included SQLite database
└── .gitignore
```

## Generated outputs

| File in `data/processed/` | Contents |
| --- | --- |
| `daily_org_kpis.csv` | Daily headcount, bench/deployment counts, attrition risk, activity counts, and budget burn rate. |
| `workforce_events.csv` | Events with dates, affected entities, reasons, and the responsible agent. |
| `agent_actions.csv` | Logged agent decisions and their business reasons. |
| `daily_insight_log.csv` | Daily text summaries. |
| `employees_final_state.csv` | Employee state at the end of the simulation. |

The dashboard shows the final headcount, deployed/bench counts, high-risk count, deployment trends, average risk trend, recent events, and final risk/deployment distributions. Additional metrics remain available in the CSV outputs.

## Optional examples

Run the small agent demonstration:

```bash
python mini_agent_demo.py
```

Prepare employee tenure and basic risk features:

```bash
python clean_data.py
```

`clean_data.py` writes `data/employee_features.csv`. This step is separate from the simulation, which reads `data/employees.csv` and calculates its own risk scores.

## Simulation notes

- Risk scores are rule-based simulation scores, not calibrated predictions of individual employee behavior.
- Some events and customer/project selections are random, so results can differ between runs even with the same dates.
- Changing the start date changes which historical assignments and exits are included in the initial state.
- New results appear in the dashboard only after rerunning both dashboard build scripts.
