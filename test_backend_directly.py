"""
Direct Backend Test Script
===========================
Tests the backend endpoints directly without going through the frontend.
This helps isolate whether the issue is in the backend or the frontend/network.
"""
import requests
import os
import sys

# Test configuration
API_BASE = "http://localhost:8000"
CLERK_TOKEN = "test_token_bypass"  # We'll test without auth first

print("="*80)
print("🧪 DIRECT BACKEND TEST")
print("="*80)
print()

# Test 1: Health Check
print("Test 1: Health Check")
print("-" * 40)
try:
    response = requests.get(f"{API_BASE}/health", timeout=5)
    print(f"✅ Status: {response.status_code}")
    print(f"✅ Response: {response.json()}")
except Exception as e:
    print(f"❌ Failed: {e}")
print()

# Test 2: Text Extraction (without auth - should fail with 401)
print("Test 2: Text Extraction (No Auth - expect 401)")
print("-" * 40)
try:
    response = requests.post(
        f"{API_BASE}/api/v1/web/extract/text",
        json={"text": "spent 100 on coffee"},
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"❌ Failed: {e}")
print()

# Test 3: Image Upload (without auth - should fail with 401)
print("Test 3: Image Upload (No Auth - expect 401)")
print("-" * 40)
image_path = "assests/demo4.jpg"
if os.path.exists(image_path):
    try:
        with open(image_path, 'rb') as f:
            files = {'file': ('demo4.jpg', f, 'image/jpeg')}
            response = requests.post(
                f"{API_BASE}/api/v1/web/extract/image",
                files=files,
                timeout=30
            )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Failed: {e}")
else:
    print(f"❌ Image file not found: {image_path}")
print()

# Test 4: Audio Upload (without auth - should fail with 401)
print("Test 4: Audio Upload (No Auth - expect 401)")
print("-" * 40)
audio_path = "assests/audio_demo2.ogg"
if os.path.exists(audio_path):
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': ('audio_demo2.ogg', f, 'audio/ogg')}
            response = requests.post(
                f"{API_BASE}/api/v1/web/extract/audio",
                files=files,
                timeout=30
            )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Failed: {e}")
else:
    print(f"❌ Audio file not found: {audio_path}")
print()

# Test 5: Check if server is even reachable
print("Test 5: Basic Connectivity")
print("-" * 40)
try:
    response = requests.get(f"{API_BASE}/", timeout=5)
    print(f"✅ Server is reachable")
    print(f"Status: {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"❌ Cannot connect to {API_BASE}")
    print(f"❌ Make sure the backend is running!")
except Exception as e:
    print(f"❌ Error: {e}")
print()

print("="*80)
print("📋 SUMMARY")
print("="*80)
print()
print("If you see 401 errors, that's GOOD - it means the backend is working")
print("and just needs authentication.")
print()
print("If you see connection errors, the backend is not running or not")
print("accessible on port 8000.")
print()
print("Next step: Get a real Clerk token and test with authentication.")
print()
