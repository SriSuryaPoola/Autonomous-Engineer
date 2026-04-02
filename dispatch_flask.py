import requests

# 1. Create project
res = requests.post("http://localhost:8000/api/projects", json={
    "name": "Flask Stress Test",
    "description": "QA auditing pallets/flask",
    "repository_url": "https://github.com/pallets/flask"
})
proj_id = res.json()["id"]
print(f"Created project: {proj_id}")

# 2. Dispatch task with custom workspace
res = requests.post("http://localhost:8000/api/tasks", json={
    "project_id": proj_id,
    "prompt": "Analyze flask/app.py. Generate thorough QA API tests for it.",
    "workspace": r"C:\Users\Pula Srisurya\Autonomus engineer\test_repos\flask"
})
print("Task queued:", res.json())
