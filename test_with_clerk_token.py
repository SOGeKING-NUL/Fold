"""
Backend Test with Clerk Authentication
=======================================
Tests the backend with a real Clerk token to verify end-to-end functionality.

HOW TO GET YOUR CLERK TOKEN:
1. Open your browser and go to http://localhost:3000/chat
2. Open Developer Tools (F12)
3. Go to Console tab
4. Run this command:
   
   await window.Clerk.session.getToken()
   
5. Copy the token (it will be a long string starting with "eyJ...")
6. Paste it when prompted by this script
"""
import requests
import os
import sys

API_BASE = "http://localhost:8000"

print("="*80)
print("🧪 BACKEND TEST WITH CLERK AUTHENTICATION")
print("="*80)
print()
print("To get your Clerk token:")
print("1. Open http://localhost:3000/chat in your browser")
print("2. Open Developer Tools (F12) → Console")
print("3. Run: await window.Clerk.session.getToken()")
print("4. Copy the token")
print()

token = input("Paste your Clerk token here: ").strip()

if not token:
    print("❌ No token provided. Exiting.")
    sys.exit(1)

print()
print(f"Token length: {len(token)} characters")
print(f"Token preview: {token[:50]}...")
print()

headers = {
    "Authorization": f"Bearer {token}"
}

# Test 1: Text Extraction
print("="*80)
print("Test 1: Text Extraction")
print("="*80)
try:
    response = requests.post(
        f"{API_BASE}/api/v1/web/extract/text",
        json={"text": "spent 100 on coffee"},
        headers=headers,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ SUCCESS!")
        result = response.json()
        print(f"Response: {result}")
    else:
        print(f"❌ FAILED")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")
print()

# Test 2: Image Upload
print("="*80)
print("Test 2: Image Upload (demo4.jpg)")
print("="*80)
image_path = "assests/demo4.jpg"
if os.path.exists(image_path):
    try:
        with open(image_path, 'rb') as f:
            files = {'file': ('demo4.jpg', f, 'image/jpeg')}
            response = requests.post(
                f"{API_BASE}/api/v1/web/extract/image",
                files=files,
                headers=headers,
                timeout=30
            )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ SUCCESS!")
            result = response.json()
            print(f"Amount: {result.get('extracted_data', {}).get('amount')}")
            print(f"Category: {result.get('extracted_data', {}).get('category')}")
            print(f"Message: {result.get('message')}")
        else:
            print(f"❌ FAILED")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
else:
    print(f"❌ Image file not found: {image_path}")
print()

# Test 3: Audio Upload
print("="*80)
print("Test 3: Audio Upload (audio_demo2.ogg)")
print("="*80)
audio_path = "assests/audio_demo2.ogg"
if os.path.exists(audio_path):
    try:
        with open(audio_path, 'rb') as f:
            files = {'file': ('audio_demo2.ogg', f, 'audio/ogg')}
            response = requests.post(
                f"{API_BASE}/api/v1/web/extract/audio",
                files=files,
                headers=headers,
                timeout=60  # Audio processing takes longer
            )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ SUCCESS!")
            result = response.json()
            print(f"Transcript: {result.get('extracted_data', {}).get('transcript', 'N/A')[:100]}")
            print(f"Amount: {result.get('extracted_data', {}).get('amount')}")
            print(f"Category: {result.get('extracted_data', {}).get('category')}")
            print(f"Message: {result.get('message')}")
        else:
            print(f"❌ FAILED")
            print(f"Response: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
else:
    print(f"❌ Audio file not found: {audio_path}")
print()

print("="*80)
print("📋 TEST COMPLETE")
print("="*80)
print()
print("If all tests passed, the backend is working correctly!")
print("The issue is likely in the frontend → backend communication.")
print()
