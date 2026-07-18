import json
import os
import sys

def verify_portals():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    portals_path = os.path.join(current_dir, "app", "portals.json")
    
    print(f"Reading portals file: {portals_path}")
    if not os.path.exists(portals_path):
        print("CRITICAL: portals.json does not exist!")
        sys.exit(1)
        
    with open(portals_path, "r", encoding="utf-8") as f:
        portals = json.load(f)
        
    print(f"Loaded {len(portals)} portal mappings.")
    
    # 1. Check count
    if len(portals) != 48:
        print(f"ERROR: Expected exactly 48 mappings, but found {len(portals)}.")
        sys.exit(1)
        
    cities = {"Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad"}
    categories = {
        "Water & Sanitation",
        "Electricity & Power",
        "Roads & Drainage",
        "Waste Management",
        "Public Safety",
        "Other"
    }
    
    # 2. Check structure and coverages
    seen = set()
    errors = 0
    for idx, entry in enumerate(portals):
        city = entry.get("city")
        category = entry.get("category")
        name = entry.get("portal_name")
        url = entry.get("portal_url")
        status = entry.get("status")
        citation = entry.get("citation")
        
        # Validations
        if not city or city not in cities:
            print(f"ERROR [Row {idx + 1}]: Invalid or missing city '{city}'")
            errors += 1
        if not category or category not in categories:
            print(f"ERROR [Row {idx + 1}]: Invalid or missing category '{category}'")
            errors += 1
        if not name:
            print(f"ERROR [Row {idx + 1}]: Missing portal_name")
            errors += 1
        if not url or not url.startswith("http"):
            print(f"ERROR [Row {idx + 1}]: Invalid or missing portal_url '{url}'")
            errors += 1
        if status not in ("Verified", "Inferred"):
            print(f"ERROR [Row {idx + 1}]: Invalid status '{status}'")
            errors += 1
        if not citation:
            print(f"ERROR [Row {idx + 1}]: Missing citation")
            errors += 1
            
        key = (city, category)
        if key in seen:
            print(f"ERROR [Row {idx + 1}]: Duplicate mapping for {(city, category)}")
            errors += 1
        seen.add(key)
        
    # Check completeness
    for c in cities:
        for cat in categories:
            if (c, cat) not in seen:
                print(f"ERROR: Missing entry for City={c}, Category={cat}")
                errors += 1
                
    if errors > 0:
        print(f"\nVerification failed with {errors} errors.")
        sys.exit(1)
    else:
        print("\nSUCCESS: All 48 portal mappings successfully verified! No duplicates, coverage is complete, and all URL structures are correct.")
        
if __name__ == "__main__":
    verify_portals()
