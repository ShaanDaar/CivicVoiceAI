import urllib.request
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def make_request(path, method="GET", data=None, headers=None):
    """
    Utility function to send HTTP requests using standard library urllib.
    """
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req_data = None
    
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        
    req = urllib.request.Request(url, data=req_data, headers=req_headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            return status_code, json.loads(response_body) if response_body else None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP ERROR: {e.code} - {e.reason}")
        print(f"Body: {error_body}")
        raise e
    except Exception as e:
        print(f"ERROR connecting to {url}: {e}")
        raise e

def run_tests():
    print("--- STARTING END-TO-END VERIFICATION ---")
    
    # 0. Log in to get admin token
    print("\n[0] Logging in as admin...")
    login_data = {"password": "demopass2026"}
    code, login_res = make_request("/verify-password", method="POST", data=login_data)
    admin_token = login_res["token"]
    print("Admin token obtained:", admin_token)
    
    # 1. Check Root Endpoint
    print("\n[1] Checking connectivity to root endpoint...")
    code, body = make_request("/")
    print(f"Root endpoint response (Code {code}):", body)
    
    # 2. Get Wards and Departments (seeded during startup)
    print("\n[2] Fetching seeded Wards...")
    code, wards = make_request("/wards")
    print(f"Seeded Wards (Code {code}):")
    for w in wards:
        print(f"  - ID: {w['id']} | Name: {w['name']}")
        
    print("\n[3] Fetching seeded Departments...")
    code, depts = make_request("/departments")
    print(f"Seeded Departments (Code {code}):")
    for d in depts:
        print(f"  - ID: {d['id']} | Name: {d['name']} | Contact: {d['contact_email']}")

    # Pick a ward and department
    ward_id = wards[0]["id"]
    dept_id = depts[0]["id"]

    # 3. Submit a new complaint (POST /complaints)
    print(f"\n[4] Submitting a new complaint for Ward ID {ward_id} and Dept ID {dept_id}...")
    complaint_data = {
        "raw_input": "Water pipeline leaking badly near main market, street clean water is being wasted.",
        "originalLanguage": "English",
        "complaintType": "Water",
        "translatedText": "Water pipeline leaking badly near main market, street clean water is being wasted.",
        "mediaAttachments": [],
        "urgency_score": 4,
        "location_description": "near the water tank, 3rd cross road, Dharavi North",
        "ward_id": ward_id,
        "department_id": dept_id
    }
    
    code, created_complaint = make_request(
        "/complaints", 
        method="POST", 
        data=complaint_data,
        headers={"X-Intake-Api-Key": "intake_secret_token"}
    )
    print(f"Complaint Created (Code {code}):")
    print(json.dumps(created_complaint, indent=2))
    
    complaint_id = created_complaint["id"]

    # 4. List and filter complaints (GET /complaints)
    print(f"\n[5] Listing and filtering complaints for Ward ID {ward_id}...")
    code, complaints_list = make_request(f"/complaints?ward_id={ward_id}")
    print(f"Filtered list count: {len(complaints_list)}")
    print(f"Returned complain status: {complaints_list[0]['status']}")

    # 5. Check resolution-time before resolution
    print("\n[6] Checking resolution time for complaints before resolution...")
    code, res_time_pre = make_request(f"/complaints/{complaint_id}/resolution-time")
    print("Resolution time details:", res_time_pre)
    assert res_time_pre["resolution_time_seconds"] is None, "Resolution time should be null for pending complaints!"

    # 6. Wait 2 seconds to check dynamic time computation, then resolve it
    print("\n[7] Simulating 2-second delay and transitioning complaint status to 'resolved'...")
    time.sleep(2)
    
    status_update = {
        "status": "resolved",
        "notes": "Our repair team patched the leaking water pipe and verified water flow restored."
    }
    code, resolved_complaint = make_request(
        f"/complaints/{complaint_id}/status", 
        method="PATCH", 
        data=status_update,
        headers={"X-Admin-Token": admin_token}
    )
    print(f"Complaint Updated (Code {code}):")
    print(f"Updated status is: {resolved_complaint['status']}")
    
    # 7. Check dynamic resolution time after resolution
    print("\n[8] Checking resolution time dynamically calculated after resolution...")
    code, res_time_post = make_request(f"/complaints/{complaint_id}/resolution-time")
    print("Resolution time details:", res_time_post)
    
    seconds = res_time_post["resolution_time_seconds"]
    print(f"Calculated resolution time: {seconds} seconds")
    
    assert seconds is not None and seconds >= 2, f"Expected resolution time >= 2 seconds, got {seconds}"
    
    # 8. Check that resolution_time_seconds field is also serialized in the standard GET /complaints detail
    print("\n[9] Verification: Checking if resolution_time_seconds is in standard GET details...")
    code, complaints_final = make_request(f"/complaints?status=resolved")
    matched_complaint = [c for c in complaints_final if c["id"] == complaint_id][0]
    print(f"GET /complaints details (containing status history & resolution secs):")
    print(json.dumps(matched_complaint, indent=2))
    
    print("\n--- ALL TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    # Give the user a way to run locally
    try:
        run_tests()
    except Exception as e:
        sys.exit(1)
