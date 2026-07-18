from sqlalchemy.orm import Session
from .models import Ward, Department, Complaint, StatusHistory

def seed_initial_data(db: Session):
    """
    Seeds the SQLite database with 5 wards and 5 departments
    as required for the CivicVoice AI initial setup.
    """
    # Define sample wards
    wards_data = [
        {"name": "Ward 1 - Dharavi North", "description": "Covers northern sectors of the Dharavi informal settlement area.", "city": "Mumbai"},
        {"name": "Ward 2 - Dharavi East", "description": "Covers eastern sectors and transit camps near Dharavi.", "city": "Mumbai"},
        {"name": "Ward 3 - Shivaji Nagar", "description": "Densely populated informal settlement area in the M-East ward.", "city": "Mumbai"},
        {"name": "Ward 4 - Kurla West", "description": "Low-lying settlements and mixed residential areas in Kurla.", "city": "Mumbai"},
        {"name": "Ward 5 - Mankhurd", "description": "Peripheral informal settlements and rehabilitation colonies.", "city": "Mumbai"},
        {"name": "Ward 6 - Majestic", "description": "Central transport hub and commercial area in Bengaluru.", "city": "Bengaluru"},
        {"name": "Ward 7 - Karol Bagh", "description": "Densely populated residential and commercial district in Delhi.", "city": "Delhi"},
        {"name": "Ward 8 - Gachibowli", "description": "IT corridor and mixed settlement area in Hyderabad.", "city": "Hyderabad"},
        {"name": "Ward 9 - T. Nagar", "description": "Shopping and residential hub with drainage issues in Chennai.", "city": "Chennai"}
    ]

    for wd in wards_data:
        # Check if ward already exists
        existing_ward = db.query(Ward).filter(Ward.name == wd["name"]).first()
        if not existing_ward:
            db_ward = Ward(name=wd["name"], description=wd["description"], city=wd["city"])
            db.add(db_ward)
            print(f"Seeding Ward: {wd['name']}")

    # Define sample departments
    departments_data = [
        {
            "name": "Water & Sanitation",
            "contact_email": "water.sanitation@civicvoice.gov",
            "contact_phone": "+91-98765-43210"
        },
        {
            "name": "Electricity & Power",
            "contact_email": "electricity@civicvoice.gov",
            "contact_phone": "+91-98765-43211"
        },
        {
            "name": "Roads & Drainage",
            "contact_email": "drainage@civicvoice.gov",
            "contact_phone": "+91-98765-43212"
        },
        {
            "name": "Waste Management",
            "contact_email": "waste@civicvoice.gov",
            "contact_phone": "+91-98765-43213"
        },
        {
            "name": "Public Safety",
            "contact_email": "safety@civicvoice.gov",
            "contact_phone": "+91-98765-43214"
        }
    ]

    for dept in departments_data:
        existing_dept = db.query(Department).filter(Department.name == dept["name"]).first()
        if not existing_dept:
            db_dept = Department(
                name=dept["name"],
                contact_email=dept["contact_email"],
                contact_phone=dept["contact_phone"]
            )
            db.add(db_dept)
            print(f"Seeding Department: {dept['name']}")

    # Flush to ensure wards/departments IDs are resolved
    db.flush()
    
    # Seed mock complaints if none exist
    if db.query(Complaint).count() == 0:
        print("Seeding mock complaints...")
        wards = db.query(Ward).all()
        depts = db.query(Department).all()
        
        ward_map = {w.name.split(" - ")[-1].strip() if " - " in w.name else w.name: w.id for w in wards}
        dept_map = {d.name: d.id for d in depts}
        
        mock_complaints = [
            {
                "raw_input": "हमारे मोहल्ले में कचरा तीन दिनों से जमा है, जिससे बहुत बदबू आ रही है और बीमारियां फैलने का खतरा है।",
                "original_transcription": "हमारे मोहल्ले में कचरा तीन दिनों से जमा है, जिससे बहुत बदबू आ रही है और बीमारियां फैलने का खतरा है।",
                "originalLanguage": "Hindi",
                "complaintType": "Sanitation",
                "translatedText": "Garbage has been piling up in our neighborhood for three days, causing a foul odor and the risk of diseases spreading.",
                "urgency_score": 4,
                "location_description": "Near the corner dump bin, Dharavi North",
                "ward_id": ward_map.get("Dharavi North", 1),
                "department_id": dept_map.get("Waste Management", 4),
                "status": "pending",
                "mediaAttachments": [{"url": "/uploads/mock_garbage.jpg", "type": "image"}]
            },
            {
                "raw_input": "रस्त्यावरील विजेचा खांब वाकला आहे आणि जिवंत तारा लटकत आहेत, मोठी दुर्घटना होऊ शकते।",
                "original_transcription": "रस्त्यावरील विजेचा खांब वाकला आहे आणि जिवंत तारा लटकत आहेत, मोठी दुर्घटना होऊ शकते।",
                "originalLanguage": "Marathi",
                "complaintType": "Electricity",
                "translatedText": "The electric pole on the road is bent and live wires are hanging, a major accident could happen.",
                "urgency_score": 5,
                "location_description": "Opposite transit camp road, Dharavi East",
                "ward_id": ward_map.get("Dharavi East", 2),
                "department_id": dept_map.get("Electricity & Power", 2),
                "status": "in-progress",
                "mediaAttachments": [{"url": "/uploads/mock_sparking.jpg", "type": "image"}]
            },
            {
                "raw_input": "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್ ಒಡೆದು ಹೋಗಿ ನೀರು ವ್ಯರ್ಥವಾಗುತ್ತಿದೆ. ದಯವಿಟ್ಟು ಸರಿಪಡಿಸಿ।",
                "original_transcription": "ನಮ್ಮ ಬೀದಿಯಲ್ಲಿ ಕುಡಿಯುವ ನೀರಿನ ಪೈಪ್ ಒಡೆದು ಹೋಗಿ ನೀರು ವ್ಯರ್ಥವಾಗುತ್ತಿದೆ. ದಯವಿಟ್ಟು ಸರಿಪಡಿಸಿ।",
                "originalLanguage": "Kannada",
                "complaintType": "Water",
                "translatedText": "The drinking water pipe on our street has burst and water is being wasted. Please fix it.",
                "urgency_score": 3,
                "location_description": "Shivaji Nagar 3rd cross road",
                "ward_id": ward_map.get("Shivaji Nagar", 3),
                "department_id": dept_map.get("Water & Sanitation", 1),
                "status": "resolved",
                "mediaAttachments": [{"url": "/uploads/mock_water_leak.jpg", "type": "image"}]
            },
            {
                "raw_input": "சாலையில் பெரிய பள்ளம் உள்ளது, இருசக்கர வாகனங்கள் விழுந்து விபத்துக்குள்ளாகின்றன।",
                "original_transcription": "சாலையில் பெரிய பள்ளம் உள்ளது, இருசக்கர வாகனங்கள் விழுந்து விபத்துக்குள்ளாகின்றன।",
                "originalLanguage": "Tamil",
                "complaintType": "Roads",
                "translatedText": "There is a huge pothole on the road, two-wheelers are falling and getting into accidents.",
                "urgency_score": 4,
                "location_description": "Near Mankhurd railway station road",
                "ward_id": ward_map.get("Mankhurd", 5),
                "department_id": dept_map.get("Roads & Drainage", 3),
                "status": "pending",
                "mediaAttachments": [{"url": "/uploads/mock_pothole.jpg", "type": "image"}]
            },
            {
                "raw_input": "Street lights in the main alley have not been working for a week, making it pitch dark and unsafe for women at night.",
                "original_transcription": None,
                "originalLanguage": "English",
                "complaintType": "Public Safety",
                "translatedText": "Street lights in the main alley have not been working for a week, making it pitch dark and unsafe for women at night.",
                "urgency_score": 4,
                "location_description": "Kurla West, Lane 4 near school",
                "ward_id": ward_map.get("Kurla West", 4),
                "department_id": dept_map.get("Public Safety", 5),
                "status": "pending",
                "mediaAttachments": [{"url": "/uploads/mock_dark_alley.jpg", "type": "image"}]
            }
        ]
        
        for comp_data in mock_complaints:
            db_comp = Complaint(
                raw_input=comp_data["raw_input"],
                original_transcription=comp_data["original_transcription"],
                originalLanguage=comp_data["originalLanguage"],
                complaintType=comp_data["complaintType"],
                translatedText=comp_data["translatedText"],
                mediaAttachments=comp_data["mediaAttachments"],
                urgency_score=comp_data["urgency_score"],
                classification_method="llm",
                location_description=comp_data["location_description"],
                ward_id=comp_data["ward_id"],
                department_id=comp_data["department_id"],
                status=comp_data["status"]
            )
            db.add(db_comp)
            db.flush()
            
            hist = StatusHistory(
                complaint_id=db_comp.id,
                status=db_comp.status,
                notes="Seed data complaint initialized."
            )
            db.add(hist)
        
    db.commit()
    print("Database seeding completed.")
