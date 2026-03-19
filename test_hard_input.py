from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_hard_extraction():
    payload = {
        "text": "Hey team, this is Elena Rodriguez speaking. I've been with the company since 2018, primarily focusing on cloud infrastructure, Kubernetes, and Golang backend services. I recently took on the role of Principal Systems Architect. Before this, I spent about 2 years at an agency doing basic React. I've been leading the migration to AWS over the past 3 months. Anyway, the summary is that I'll be out of office next week.",
        "schema": {
            "name": "string",
            "skills": "list[string]",
            "experience_years": "int",
            "role": "string",
            "summary": "string"
        }
    }
    
    print("Testing with Hard Input...")
    response = client.post("/api/v1/extract", json=payload)
    print("STATUS CODE:", response.status_code)
    try:
        print("RESPONSE JSON:", json.dumps(response.json(), indent=2))
    except Exception:
        print("RESPONSE TEXT:", response.text)

if __name__ == "__main__":
    test_hard_extraction()
