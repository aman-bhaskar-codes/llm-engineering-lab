import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"

async def test_minimal_extraction():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Login (or use existing if we know it)
        # Assuming signup/login works from previous tests
        print("--- Testing Authenticated Extraction ---")
        login_res = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "prod_user_final@example.com",
            "password": "securepassword123"
        })
        if login_res.status_code != 200:
            print(f"Login failed: {login_res.text}")
            return
        
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Simple Extraction
        print("\n--- 2. Simple Text Extraction ---")
        payload = {
            "text": "The project deadline is April 15th, 2026. The budget is $50,000.",
            "mode": "simple"
        }
        res = await client.post(f"{BASE_URL}/extract", json=payload, headers=headers)
        
        print(f"Status: {res.status_code}")
        data = res.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # Verify schema
        result = data.get("result", {})
        assert "data" in result
        assert "confidence" in result
        assert "valid" in result
        assert "issues" in result
        print("✅ SUCCESS: Schema matches Final Output Format mandate.")

if __name__ == "__main__":
    asyncio.run(test_minimal_extraction())
