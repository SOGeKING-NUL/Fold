"""
CORS and Header Size Test
==========================
Tests if CORS is configured correctly and if large headers are accepted.
"""
import requests
import os

API_BASE = "http://localhost:8000"

print("="*80)
print("🧪 CORS AND HEADER SIZE TEST")
print("="*80)
print()

# Test 1: CORS Preflight
print("Test 1: CORS Preflight (OPTIONS request)")
print("-" * 40)
try:
    response = requests.options(
        f"{API_BASE}/api/v1/web/extract/text",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        },
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"CORS Headers:")
    for header, value in response.headers.items():
        if 'access-control' in header.lower():
            print(f"  {header}: {value}")
    
    if response.status_code == 200:
        print("✅ CORS preflight passed")
    else:
        print("⚠️  CORS preflight returned non-200 status")
except Exception as e:
    print(f"❌ Failed: {e}")
print()

# Test 2: Large Authorization Header
print("Test 2: Large Authorization Header (simulating Clerk token)")
print("-" * 40)
# Create a fake token similar in size to a real Clerk token (830 chars)
fake_token = "eyJ" + "x" * 827  # 830 characters total
print(f"Fake token length: {len(fake_token)} characters")

try:
    response = requests.post(
        f"{API_BASE}/api/v1/web/extract/text",
        json={"text": "test"},
        headers={
            "Authorization": f"Bearer {fake_token}",
            "Origin": "http://localhost:3000"
        },
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    
    if response.status_code == 401:
        print("✅ Server accepted large header (returned 401 for invalid token)")
    elif "header too large" in response.text.lower():
        print("❌ Server rejected large header!")
    else:
        print(f"⚠️  Unexpected response")
except Exception as e:
    print(f"❌ Failed: {e}")
print()

# Test 3: Very Large Header (to find the limit)
print("Test 3: Very Large Header (finding the limit)")
print("-" * 40)
for size_kb in [1, 5, 10, 20, 50, 100]:
    fake_token = "x" * (size_kb * 1024)
    try:
        response = requests.post(
            f"{API_BASE}/api/v1/web/extract/text",
            json={"text": "test"},
            headers={"Authorization": f"Bearer {fake_token}"},
            timeout=5
        )
        if "header too large" in response.text.lower():
            print(f"  {size_kb}KB: ❌ TOO LARGE")
            break
        else:
            print(f"  {size_kb}KB: ✅ Accepted")
    except Exception as e:
        print(f"  {size_kb}KB: ❌ Error: {e}")
        break
print()

# Test 4: Check actual request from browser
print("Test 4: Simulating Browser Request")
print("-" * 40)
print("This simulates exactly what the browser sends...")
try:
    response = requests.post(
        f"{API_BASE}/api/v1/web/extract/text",
        json={"text": "spent 100 on coffee"},
        headers={
            "Content-Type": "application/json",
            "Origin": "http://localhost:3000",
            "Referer": "http://localhost:3000/chat",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            # No Authorization header - should get 401
        },
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
    
    if response.status_code == 401:
        print("✅ Server is reachable from browser-like request")
    else:
        print("⚠️  Unexpected response")
except Exception as e:
    print(f"❌ Failed: {e}")
print()

print("="*80)
print("📋 ANALYSIS")
print("="*80)
print()
print("If Test 2 shows 'header too large', the h11 patch didn't work.")
print("If Test 2 shows 401, the server accepts large headers correctly.")
print("If Test 4 fails, there might be a network/firewall issue.")
print()
