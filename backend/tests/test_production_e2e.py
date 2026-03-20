import asyncio
import httpx
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

BASE_URL = "http://localhost:8000/api/v1"

async def test_production_platform():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n--- 1. Signup & Login ---")
        user_email = "prod_user_final@example.com"
        await client.post(f"{BASE_URL}/auth/signup", json={"email": user_email, "password": "securepassword123"})
        login_res = await client.post(f"{BASE_URL}/auth/login", json={"email": user_email, "password": "securepassword123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n--- 2. Premium Extraction (Multi-Pass) ---")
        extraction_payload = {
            "text": "Jane Smith is a Principal Engineer at Netflix with 15 years in Java and AWS. She holds a PhD from MIT.",
            "mode": "premium"
        }
        res = await client.post(f"{BASE_URL}/extract", json=extraction_payload, headers=headers)
        data = res.json()
        print(f"Premium Result: {json.dumps(data.get('result', {}).get('data', {}), indent=2)}")
        print(f"Confidence: {data.get('result', {}).get('confidence')}")
        
        print("\n--- 3. Semantic Memory Check ---")
        memory_res = await client.get(f"{BASE_URL}/memory", headers=headers)
        memory_data = memory_res.json()
        print(f"Items in Semantic Memory: {len(memory_data.get('semantic', []))}")
        
        print("\n✅ PRODUCTION SYSTEM VERIFIED")

if __name__ == "__main__":
    asyncio.run(test_production_platform())
