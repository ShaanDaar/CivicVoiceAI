import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

SAMPLE_COMPLAINTS = [
    {
        "raw_input": "Water pipeline leaking badly near main market, street clean water is being wasted for two days.",
        "ward_id": 1,
        "description": "Ex: Water Leakage (Expected: category 'water', high urgency, routed to Water & Sanitation)"
    },
    {
        "raw_input": "The sewage line is blocked and overflows on the road. It creates a massive health hazard for all of us.",
        "ward_id": 2,
        "description": "Ex: Blocked Gutter/Sewage (Expected: category 'drainage', high urgency, routed to Roads & Drainage)"
    },
    {
        "raw_input": "No electricity in our street since yesterday evening. Sparks are coming out of a main pole wire creating danger.",
        "ward_id": 3,
        "description": "Ex: Live Wire / Power Outage (Expected: category 'electricity', high urgency, routed to Electricity & Power)"
    },
    {
        "raw_input": "Garbage has piled up around the corner trash bin and smells terrible. It has been sitting here for a week.",
        "ward_id": 4,
        "description": "Ex: Garbage Accumulation (Expected: category 'sanitation', mid urgency, routed to Waste Management)"
    },
    {
        "raw_input": "The main road has a huge pothole. Cars are getting damaged when they pass over it, causing safety risks.",
        "ward_id": 5,
        "description": "Ex: Pothole / Road damage (Expected: category 'roads', mid urgency, routed to Roads & Drainage)"
    }
]

def make_post_request(path, data):
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-Intake-Api-Key": "intake_secret_token"
    }
    req_data = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            return status_code, json.loads(response_body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {error_body}")
        raise e
    except Exception as e:
        print(f"Network error: {e}")
        raise e

def run_agent_tests():
    print("=====================================================================")
    print("           CIVICVOICE AI - LANGGRAPH AGENT INTEGRATION TEST          ")
    print("=====================================================================\n")
    
    success = True
    for idx, case in enumerate(SAMPLE_COMPLAINTS, 1):
        print(f"[{idx}] TEST CASE: {case['description']}")
        print(f"    Raw Input: '{case['raw_input']}'")
        
        payload = {
            "raw_input": case["raw_input"],
            "ward_id": case["ward_id"]
        }
        
        try:
            status_code, result = make_post_request("/classify", payload)
            print(f"    Status: {status_code} (Success)")
            print(f"    Detected Category/Type  : {result.get('complaintType')}")
            print(f"    Generated Urgency Score : {result.get('urgency_score')}/5")
            print(f"    Original Language       : {result.get('originalLanguage')}")
            print(f"    Translated Text         : '{result.get('translatedText')}'")
            print(f"    Routed Department ID    : {result.get('department_id')}")
            print(f"    Routed Department Name  : {result.get('department_name')}")
            print(f"    Method Used             : {result.get('classification_method')}")
            print(f"    Reasoning               : {result.get('reasoning')}")
        except Exception as e:
            print(f"    Result: FAILED to classify: {e}")
            success = False
            
        print("-" * 69 + "\n")
        
    if success:
        print("ALL AGENT CLASSIFICATIONS PROCESSED SUCCESSFULLY!")
    else:
        print("SOME CLASSIFICATIONS ENCOUNTERED ERRORS.")
        sys.exit(1)

if __name__ == "__main__":
    run_agent_tests()
