import requests

res = requests.post("http://localhost:8000/api/projects", json={
    "name": "FastAPI Stress Test",
    "description": "QA auditing tiangolo/fastapi",
    "repository_url": "https://github.com/tiangolo/fastapi"
})
proj_id = res.json()["id"]
print(f"Created project: {proj_id}")

res = requests.post("http://localhost:8000/api/tasks", json={
    "project_id": proj_id,
    "prompt": "Analyze fastapi/routing.py. Generate thorough QA API tests.",
    "workspace": r"C:\Users\Pula Srisurya\Autonomus engineer\test_repos\fastapi"
})
print("Task queued:", res.json())
