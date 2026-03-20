#!/usr/bin/env python3
"""End-to-end system test: Auth → Extract → Conversations → Memory."""

import httpx
import json
import sys

BASE = "http://127.0.0.1:8000/api/v1"

def main():
    print("=" * 60)
    print("🧪 FULL SYSTEM E2E TEST")
    print("=" * 60)

    # 1. LOGIN
    print("\n1️⃣  LOGIN...")
    r = httpx.post(f"{BASE}/auth/login", json={"email": "test@example.com"}, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   ❌ Login failed: {r.text}")
        sys.exit(1)
    login_data = r.json()
    token = login_data["access_token"]
    user_id = login_data["user_id"]
    print(f"   ✅ Token: {token[:20]}...")
    print(f"   ✅ User ID: {user_id}")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. EXTRACT TEXT
    print("\n2️⃣  EXTRACT TEXT...")
    payload = {
        "text": "So, talking about John — he's someone who's been coding for quite a while now. I think around four years or maybe slightly more. Most of his work revolves around Python, databases like SQL, and lately he's been building APIs using FastAPI. Academically, he studied Computer Science at Delhi University and finished around 2019, if I remember correctly."
    }
    r = httpx.post(f"{BASE}/extract", json=payload, headers=headers, timeout=60)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   ❌ Extract failed: {r.text}")
        sys.exit(1)
    extract_data = r.json()
    print(f"   ✅ Conversation ID: {extract_data.get('conversation_id')}")
    print(f"   ✅ Extraction ID: {extract_data.get('extraction_id')}")
    print(f"   ✅ Result keys: {list(extract_data.get('result', {}).keys())}")
    print(f"   📄 Data: {json.dumps(extract_data.get('result', {}).get('data'), indent=2)}")

    conv_id = extract_data.get("conversation_id")

    # 3. LIST CONVERSATIONS
    print("\n3️⃣  LIST CONVERSATIONS...")
    r = httpx.get(f"{BASE}/conversations", headers=headers, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        convs = r.json()
        print(f"   ✅ Total conversations: {len(convs)}")
        for c in convs[:3]:
            print(f"      - {c['id'][:8]}... | {c['title']}")
    else:
        print(f"   ❌ {r.text}")

    # 4. GET CONVERSATION DETAIL
    if conv_id:
        print(f"\n4️⃣  GET CONVERSATION {str(conv_id)[:8]}...")
        r = httpx.get(f"{BASE}/conversation/{conv_id}", headers=headers, timeout=10)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            detail = r.json()
            print(f"   ✅ Messages: {len(detail.get('messages', []))}")
            print(f"   ✅ Extractions: {len(detail.get('extractions', []))}")
        else:
            print(f"   ❌ {r.text}")

    # 5. CHECK SEMANTIC MEMORY
    print("\n5️⃣  CHECK SEMANTIC MEMORY...")
    r = httpx.get(f"{BASE}/memory", headers=headers, timeout=10)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        mem = r.json()
        semantic = mem.get("semantic", [])
        relationships = mem.get("relationships", [])
        print(f"   ✅ Semantic entries: {len(semantic)}")
        for s in semantic[:5]:
            print(f"      - {s['key']}: {json.dumps(s['value'])}")
        print(f"   ✅ Relationships: {len(relationships)}")
        for rel in relationships[:5]:
            print(f"      - {rel['from_value']} --[{rel['relation_type']}]--> {rel['to_value']}")
    else:
        print(f"   ❌ {r.text}")

    print("\n" + "=" * 60)
    print("🎉 E2E TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
