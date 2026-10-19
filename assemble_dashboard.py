import json

with open("dashboard_data.json") as f:
    data = json.load(f)

with open("dashboard_template.html") as f:
    html = f.read()

html = html.replace("__SIM_DATA__", f"const SIM_DATA = {json.dumps(data)};")

with open("workforce_dashboard.html", "w") as f:
    f.write(html)

print("Built workforce_dashboard.html")