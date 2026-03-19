from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_messy_john():
    payload = {
        "text": "So, talking about John — he's someone who's been coding for quite a while now. I think around four years or maybe slightly more. Most of his work revolves around Python, databases like SQL, and lately he's been building APIs using FastAPI. Academically, he studied Computer Science at Delhi University and finished around 2019, if I remember correctly.",
        "schema": None
    }
    
    print("Testing with Messy Informative Input...")
    response = client.post("/api/v1/extract", json=payload)
    print("STATUS CODE:", response.status_code)
    try:
        print("RESPONSE JSON:", json.dumps(response.json(), indent=2))
    except Exception:
        print("RESPONSE TEXT:", response.text)

if __name__ == "__main__":
    test_messy_john()
