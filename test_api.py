from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_extract_endpoint():
    payload = {
        "text": "Rohit is a software engineer with 3 years experience in Python and AI",
        "schema": {
            "name": "string",
            "skills": "list[string]",
            "experience_years": "int"
        }
    }
    
    response = client.post("/api/v1/extract", json=payload)
    print("STATUS CODE:", response.status_code)
    print("RESPONSE JSON:", json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_extract_endpoint()
