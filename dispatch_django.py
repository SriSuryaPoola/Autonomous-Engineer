import requests
import time

res = requests.post("http://localhost:8000/api/projects", json={
    "name": "Django Live Run",
    "description": "Final E2E",
    "repository_url": "https://github.com/django/django"
})
proj_id = res.json()["id"]
print(f"Created project: {proj_id}")

res = requests.post("http://localhost:8000/api/tasks", json={
    "project_id": proj_id,
    "prompt": "Analyze django/core/handlers/base.py. Write a comprehensive QA test covering base request handling.",
    "workspace": r"C:\Users\Pula Srisurya\Autonomus engineer\test_repos\django"
})
print("Task queued:", res.json())
