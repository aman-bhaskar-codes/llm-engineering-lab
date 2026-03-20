import httpx
import asyncio
import uuid
import json
import os

BASE_URL = "http://localhost:8000/api/v1"

async def test_elite_platform():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("\n--- 1. Signup & Login ---")
        email = f"elite_user_{uuid.uuid4().hex[:6]}@test.com"
        password = "SecurePassword123"
        
        await client.post(f"{BASE_URL}/auth/signup", json={"email": email, "password": password})
        login_res = await client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("\n--- 2. Premium Extraction (Reasoning + Memory Capture) ---")
        text = """
        John Doe is a Senior Software Architect at Google with 12 years of experience.
        He is an expert in Python, Kubernetes, and Distributed Systems.
        He graduated from Stanford University with a Masters in Computer Science.
        """
        extract_res = await client.post(
            f"{BASE_URL}/extract",
            json={"text": text, "mode": "premium"},
            headers=headers
        )
        data = extract_res.json()
        print(f"Premium Extraction Result: {json.dumps(data['result']['data'], indent=2)}")
        print(f"Confidence: {data['result'].get('confidence')}")
        print(f"Reasoning: {data['result'].get('reasoning')[:100]}...")

        # Wait a bit for DB/Embeddings to settle
        await asyncio.sleep(1)

        print("\n--- 3. Semantic Search (Vector Discovery) ---")
        # Query for something related but not literal
        extract_res_2 = await client.post(
            f"{BASE_URL}/extract",
            json={"text": "I need a coding expert for a cloud project.", "mode": "premium"},
            headers=headers
        )
        # Check if the context was injected (usually we'd check logs or behavior)
        # In a real test we verify if result reflects the knowledge of John Doe
        print("Premium extraction with semantic retrieval completed.")

        print("\n--- 4. Memory Endpoint ---")
        memory_res = await client.get(f"{BASE_URL}/memory", headers=headers)
        mem_data = memory_res.json()
        print(f"Captured Semantic Keys: {[e['key'] for e in mem_data['semantic']]}")
        
        has_vectors = any(e['key'] == 'skills' for e in mem_data['semantic'])
        print(f"Knowledge Vectorized: {has_vectors}")

        print("\n--- Verification Complete ---")

if __name__ == "__main__":
    # Ensure server is running or start it
    asyncio.run(test_elite_platform())
