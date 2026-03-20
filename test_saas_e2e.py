#!/usr/bin/env python3
"""SaaS E2E Test: Signup → Login → Extract → Cache → Refresh → Profile → Usage."""

import httpx
import json
import uuid
import sys
import time

BASE = "http://127.0.0.1:8000/api/v1"
EMAIL = f"saas_user_{uuid.uuid4().hex[:6]}@example.com"
PASSWORD = "SecurePassword123!"

def main():
    print("=" * 60)
    print("🧪 SAAS PLATFORM E2E TEST")
    print("=" * 60)

    # 1. SIGNUP
    print(f"\n1️⃣  SIGNUP ({EMAIL})...")
    r = httpx.post(
        f"{BASE}/auth/signup", 
        json={"email": EMAIL, "password": PASSWORD}, 
        timeout=10
    )
    if r.status_code != 200:
        print(f"   ❌ Signup failed: {r.text}")
        sys.exit(1)
    signup_data = r.json()
    print(f"   ✅ Tokens received. User ID: {signup_data['user_id']}")

    # 2. LOGIN
    print("\n2️⃣  LOGIN...")
    r = httpx.post(
        f"{BASE}/auth/login", 
        json={"email": EMAIL, "password": PASSWORD}, 
        timeout=10
    )
    if r.status_code != 200:
        print(f"   ❌ Login failed: {r.text}")
        sys.exit(1)
    login_data = r.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]
    print(f"   ✅ Login successful.")

    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 3. PROFILE (/me)
    print("\n3️⃣  GET PROFILE (/me)...")
    r = httpx.get(f"{BASE}/me", headers=auth_headers, timeout=10)
    if r.status_code == 200:
        print(f"   ✅ Profile retrieved: {r.json()['email']}")
    else:
        print(f"   ❌ {r.text}")

    # 4. EXTRACTION (MISS)
    print("\n4️⃣  EXTRACTION (Cache Miss)...")
    text = "John is a senior Python developer from Delhi University (2019) with 4 years of experience in FastAPI and SQL."
    r = httpx.post(
        f"{BASE}/extract", 
        json={"text": text, "mode": "simple"}, 
        headers=auth_headers,
        timeout=60
    )
    if r.status_code != 200:
        print(f"   ❌ Extraction failed: {r.text}")
        sys.exit(1)
    res = r.json()
    print(f"   ✅ Extraction done. Cached: {res.get('cached')}")

    # 5. EXTRACTION (HIT)
    print("\n5️⃣  EXTRACTION (Cache Hit)...")
    r = httpx.post(
        f"{BASE}/extract", 
        json={"text": text, "mode": "simple"}, 
        headers=auth_headers,
        timeout=10
    )
    if r.status_code == 200:
        res = r.json()
        print(f"   ✅ Extraction done. Cached: {res.get('cached')}")
        if not res.get("cached"):
            print("   ⚠️  Warning: Expected cache hit but got miss!")
    else:
        print(f"   ❌ {r.text}")

    # 6. TOKEN REFRESH
    print("\n6️⃣  TOKEN REFRESH...")
    r = httpx.post(
        f"{BASE}/auth/refresh", 
        json={"refresh_token": refresh_token},
        timeout=10
    )
    if r.status_code == 200:
        new_tokens = r.json()
        print("   ✅ Access token refreshed.")
        auth_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    else:
        print(f"   ❌ {r.text}")

    # 7. RATE LIMIT TEST (Optional/Burst)
    print("\n7️⃣  RATE LIMIT TEST (Burst 5 reqs)...")
    for i in range(5):
        r = httpx.post(
            f"{BASE}/extract", 
            json={"text": f"Iteration {i}", "mode": "simple"}, 
            headers=auth_headers,
            timeout=10
        )
        if r.status_code == 429:
            print(f"   ✅ Rate limit hit at request {i+1}")
            break
    else:
        print("   ℹ️  Rate limit not hit (limit is likely higher than 5).")

    print("\n" + "=" * 60)
    print("🎉 SAAS PLATFORM E2E TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
