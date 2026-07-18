import os
import json
import urllib.request
import urllib.parse
import sys
import io

# Configure stdout to use UTF-8 on Windows to handle Hindi/Marathi/Kannada characters
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
TEST_AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_audio")

TEST_CASES = [
    {
        "filename": "hi_complaint.mp3",
        "ward_id": 4,
        "lang": "Hindi",
        "description": "Ex: Hindi (Sanitation/Odor)"
    },
    {
        "filename": "mr_complaint.mp3",
        "ward_id": 3,
        "lang": "Marathi",
        "description": "Ex: Marathi (Sparking live pole danger)"
    },
    {
        "filename": "kn_complaint.mp3",
        "ward_id": 1,
        "lang": "Kannada",
        "description": "Ex: Kannada (Broken water pipe waste)"
    }
]

def post_multipart(path, file_path, filename):
    """
    Submits a file via raw multipart form-data upload without external library dependencies (requests).
    """
    url = f"{BASE_URL}{path}"
    boundary = "----WebKitFormBoundaryCIVICVOICEAITEST"
    
    with open(file_path, "rb") as f:
        file_content = f.read()
        
    part_head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: audio/mpeg\r\n\r\n"
    ).encode("utf-8")
    
    part_foot = f"\r\n--{boundary}--\r\n".encode("utf-8")
    body = part_head + file_content + part_foot
    
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
        "X-Intake-Api-Key": "intake_secret_token"
    }
    
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            return res.getcode(), json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        raise e
 
def post_json(path, data):
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-Intake-Api-Key": "intake_secret_token"
    }
    req_body = json.dumps(data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as res:
            return res.getcode(), json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
        raise e

def run_tests():
    print("=====================================================================")
    print("      CIVICVOICE AI - MULTIMODAL AUDIO PIPELINE INTEGRATION TEST     ")
    print("=====================================================================\n")
    
    # Check if files exist
    for tc in TEST_CASES:
        fp = os.path.join(TEST_AUDIO_DIR, tc["filename"])
        if not os.path.exists(fp):
            print(f"Error: Test file not found at {fp}. Please run generate_test_audio.py first.")
            sys.exit(1)
            
    all_success = True
    
    # 1. Run success files
    for idx, tc in enumerate(TEST_CASES, 1):
        print(f"[{idx}] TEST CASE ({tc['description']}):")
        print("    [Verification Category]: Synthetic Clean Audio (gTTS Generated)")
        print(f"    Target File: {tc['filename']}")
        
        file_path = os.path.join(TEST_AUDIO_DIR, tc['filename'])
        
        try:
            # 1a. Call /transcribe
            print("    -> Calling POST /transcribe ...")
            sc, trans_res = post_multipart("/transcribe", file_path, tc["filename"])
            print(f"       Status: {sc} (Success)")
            print(f"       Original Text : '{trans_res.get('original_transcription')}'")
            print(f"       English Trans : '{trans_res.get('english_translation')}'")
            print(f"       Detected Lang : '{trans_res.get('originalLanguage')}'")
            assert trans_res.get("transcription_success") is True, "Expected transcription_success to be True"
            
            # 1b. Call /classify
            print("    -> Calling POST /classify ...")
            classify_payload = {
                "raw_input": trans_res["english_translation"],
                "ward_id": tc["ward_id"],
                "transcription_success": True
            }
            sc_c, class_res = post_json("/classify", classify_payload)
            print(f"       Status: {sc_c} (Success)")
            print(f"       Extracted Cat : {class_res.get('complaintType')}")
            print(f"       Urgency Score : {class_res.get('urgency_score')}/5")
            print(f"       Department ID : {class_res.get('department_id')} ({class_res.get('department_name')})")
            
            # 1c. Call /complaints (persist)
            print("    -> Calling POST /complaints (persist in DB) ...")
            complaint_payload = {
                "raw_input": trans_res["english_translation"],
                "original_transcription": trans_res["original_transcription"],
                "originalLanguage": trans_res["originalLanguage"],
                "complaintType": class_res["complaintType"],
                "translatedText": trans_res["english_translation"],
                "mediaAttachments": [],
                "urgency_score": class_res["urgency_score"],
                "classification_method": class_res["classification_method"],
                "location_description": "Verification test sandbox uploader",
                "ward_id": tc["ward_id"],
                "department_id": class_res["department_id"],
                "transcription_success": True
            }
            sc_cr, res_comp = post_json("/complaints", complaint_payload)
            print(f"       Status: {sc_cr} (Success)")
            print(f"       Saved ID      : {res_comp.get('id')}")
            print(f"       Saved Status  : {res_comp.get('status')}")
            print(f"       Audit Logs    : {len(res_comp.get('status_history', []))} records")
            
        except Exception as e:
            print(f"    RESULT: FAILED test case: {e}")
            all_success = False
            
        print("-" * 69 + "\n")
        
    # 2. Run error fallback file triage test
    print("[4] TEST CASE (Failed Transcription - Explicit Fallback path):")
    print("    [Verification Category]: Simulation of Noisy/Invalid Audio Note")
    
    try:
        # Mock failed transcription result data
        mock_failed_trans = {
            "original_transcription": "",
            "english_translation": "Fallback: Audio transcription failed. Queued for manual triage.",
            "originalLanguage": "Unknown",
            "transcription_success": False
        }
        
        print("    -> Calling POST /classify with success=False ...")
        classify_payload = {
            "raw_input": mock_failed_trans["english_translation"],
            "ward_id": 1,
            "transcription_success": False
        }
        sc_c, class_res = post_json("/classify", classify_payload)
        print(f"       Status: {sc_c} (Success)")
        print(f"       Extracted Cat : {class_res.get('complaintType')} (expected: Other)")
        print(f"       Urgency Score : {class_res.get('urgency_score')}/5 (expected: 1)")
        print(f"       Department    : {class_res.get('department_name')} (expected: Public Safety)")
        
        # Call /complaints (persist)
        print("    -> Calling POST /complaints (persist in DB) ...")
        complaint_payload = {
            "raw_input": mock_failed_trans["english_translation"],
            "original_transcription": mock_failed_trans["original_transcription"],
            "originalLanguage": mock_failed_trans["originalLanguage"],
            "complaintType": class_res["complaintType"],
            "translatedText": mock_failed_trans["english_translation"],
            "mediaAttachments": [],
            "urgency_score": class_res["urgency_score"],
            "classification_method": class_res["classification_method"],
            "location_description": "Verification test sandbox fallback",
            "ward_id": 1,
            "department_id": class_res["department_id"],
            "transcription_success": False
        }
        sc_cr, res_comp = post_json("/complaints", complaint_payload)
        print(f"       Status: {sc_cr} (Success)")
        print(f"       Saved ID      : {res_comp.get('id')}")
        print(f"       Saved Status  : {res_comp.get('status')} (expected: manual_review)")
        print(f"       Audit Notes   : '{res_comp.get('status_history')[0].get('notes')}'")
        
        assert res_comp.get("status") == "manual_review","Expected status to be manual_review"
        print("    RESULT: Fallback routing and status assignment success!")
        
    except Exception as e:
        print(f"    RESULT: FAILED testing fallback route: {e}")
        all_success = False
        
    print("-" * 69 + "\n")
    
    if all_success:
        print("ALL MULTIMODAL PIPELINE VERIFICATIONS COMPLETED SUCCESSFULLY!")
    else:
        print("SOME VERIFICATION CHECKS RETURNED ERRORS.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
