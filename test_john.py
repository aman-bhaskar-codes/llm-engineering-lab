from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_john_extraction():
    payload = {
        "text": """Profile Summary:

A highly motivated individual with strong backend development skills. Over the past few years (~4 yrs), John Doe has contributed to multiple projects involving Python-based systems, relational databases (SQL), and API frameworks such as FastAPI.

Education:
B.Sc. Computer Science, Delhi University (2016–2019)

Additional Notes:
- Occasionally mentors junior developers
- Interested in distributed systems""",
        "schema": None
    }
    
    print("Testing with John's Input...")
    response = client.post("/api/v1/extract", json=payload)
    print("STATUS CODE:", response.status_code)
    try:
        print("RESPONSE JSON:", json.dumps(response.json(), indent=2))
    except Exception:
        print("RESPONSE TEXT:", response.text)

if __name__ == "__main__":
    test_john_extraction()
