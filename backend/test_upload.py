import os
import requests

BASE_URL = "http://127.0.0.1:8000"

def run_upload_test():
    print("=====================================================================")
    print("             CIVICVOICE AI - SUPABASE STORAGE UPLOAD TEST             ")
    print("=====================================================================\n")
    
    # 1. Register a test citizen
    register_url = f"{BASE_URL}/auth/register"
    register_payload = {
        "full_name": "Test Citizen Upload",
        "email": "test_citizen_upload@example.com",
        "password": "testpassword123",
        "ward_id": 1,
        "role": "citizen"
    }
    
    print("Registering test citizen...")
    reg_res = requests.post(register_url, json=register_payload)
    if reg_res.status_code == 201:
        print("Registration successful.")
    elif reg_res.status_code == 400 and "already registered" in reg_res.text.lower():
        print("User already registered. Proceeding to login...")
    else:
        print(f"Registration failed: {reg_res.status_code} - {reg_res.text}")
        return

    # 2. Login to get a token
    login_url = f"{BASE_URL}/auth/login"
    login_payload = {
        "email": "test_citizen_upload@example.com",
        "password": "testpassword123"
    }
    
    print("Logging in to get JWT token...")
    login_res = requests.post(login_url, json=login_payload)
    if not login_res.ok:
        print(f"FAILED to login: {login_res.status_code} - {login_res.text}")
        return
        
    token = login_res.json()["access_token"]
    print(f"JWT token obtained successfully: {token[:12]}...")
    
    # 3. Upload a dummy test image
    upload_url = f"{BASE_URL}/complaints/upload"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # 1x1 pixel transparent dummy GIF bytes
    dummy_gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    
    files = {
        "file": ("test_image.gif", dummy_gif_bytes, "image/gif")
    }
    
    print("\nUploading dummy test image to /complaints/upload ...")
    upload_res = requests.post(upload_url, headers=headers, files=files)
    if not upload_res.ok:
        print(f"FAILED to upload: {upload_res.status_code} - {upload_res.text}")
        return
        
    res_data = upload_res.json()
    print(f"Upload SUCCESS! Response: {res_data}")
    print(f"\nReturned URL: {res_data.get('url')}")
    print(f"Returned Type: {res_data.get('type')}")
    
    # 4. Verify it is a Supabase Storage URL
    url = res_data.get('url', '')
    if "supabase.co" in url:
        print("\nSUCCESS: Verified that the returned URL is a real Supabase Storage public URL!")
    else:
        print("\nWARNING: Returned URL is local or did not use Supabase storage!")

if __name__ == "__main__":
    run_upload_test()
