import sqlite3
import os
import json
import sys

# Ensure backend directory is in sys.path so we can import from app
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

db_path = os.path.join(backend_dir, "civicvoice.db")
print(f"Active SQLite DB Path: {db_path}")

def run_db_schema_migration():
    if not os.path.exists(db_path):
        print("Database file does not exist yet. No migration needed.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Rename columns if they exist
    print("Checking for legacy columns to rename...")
    
    # Check current columns in complaints table
    cursor.execute("PRAGMA table_info(complaints);")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "issue_type" in columns:
        try:
            cursor.execute("ALTER TABLE complaints RENAME COLUMN issue_type TO complaintType;")
            print("Successfully renamed 'issue_type' to 'complaintType'.")
        except Exception as e:
            print(f"Error renaming issue_type: {e}")
            sys.exit(1)
            
    if "detected_language" in columns:
        try:
            cursor.execute("ALTER TABLE complaints RENAME COLUMN detected_language TO originalLanguage;")
            print("Successfully renamed 'detected_language' to 'originalLanguage'.")
        except Exception as e:
            print(f"Error renaming detected_language: {e}")
            sys.exit(1)

    # 2. Add new columns if they do not exist
    print("Checking for new columns to add...")
    cursor.execute("PRAGMA table_info(complaints);")
    columns = [col[1] for col in cursor.fetchall()]

    if "translatedText" not in columns:
        try:
            cursor.execute("ALTER TABLE complaints ADD COLUMN translatedText TEXT;")
            print("Successfully added 'translatedText' column.")
        except Exception as e:
            print(f"Error adding translatedText: {e}")
            sys.exit(1)

    if "mediaAttachments" not in columns:
        try:
            cursor.execute("ALTER TABLE complaints ADD COLUMN mediaAttachments TEXT;")
            print("Successfully added 'mediaAttachments' column.")
        except Exception as e:
            print(f"Error adding mediaAttachments: {e}")
            sys.exit(1)

    # 3. Backfill data
    print("Backfilling database values to match new enums...")
    cursor.execute("SELECT id, complaintType, originalLanguage, raw_input FROM complaints;")
    rows = cursor.fetchall()
    
    for row in rows:
        row_id, comp_type, orig_lang, raw_in = row
        
        # Mapping old issue_type to complaintType enum
        new_type = "Other"
        if comp_type:
            c_lower = comp_type.lower().strip()
            if "water" in c_lower:
                new_type = "Water"
            elif "sanitation" in c_lower:
                new_type = "Sanitation"
            elif "electricity" in c_lower:
                new_type = "Electricity"
            elif "drainage" in c_lower or "roads" in c_lower:
                new_type = "Roads"
            elif "safety" in c_lower:
                new_type = "Public Safety"
            else:
                new_type = "Other"

        # Mapping old detected_language to originalLanguage enum
        new_lang = "English"
        if orig_lang:
            l_cap = orig_lang.strip().capitalize()
            valid_langs = {"English", "Hindi", "Kannada", "Tamil", "Telugu", "Bengali", "Marathi", "Gujarati", "Urdu", "Malayalam", "Punjabi", "Odia", "Unknown"}
            if l_cap in valid_langs:
                new_lang = l_cap
            else:
                new_lang = "Unknown"

        # translatedText defaults to raw_input (which is the English translation in existing seeds)
        new_translation = raw_in

        # mediaAttachments defaults to empty array JSON
        new_media = "[]"

        cursor.execute(
            """
            UPDATE complaints 
            SET complaintType = ?, originalLanguage = ?, translatedText = ?, mediaAttachments = ? 
            WHERE id = ?;
            """,
            (new_type, new_lang, new_translation, new_media, row_id)
        )
        print(f"  [Backfilled Row ID {row_id}]: complaintType={new_type}, originalLanguage={new_lang}")

    conn.commit()
    conn.close()
    print("Schema updates and SQLite backfills completed successfully.")

def run_post_migration_validation():
    print("\n--- Starting Post-Migration Validation ---")
    
    # Import SQLAlchemy models and Pydantic schemas
    from app.database import SessionLocal
    from app.models import Complaint
    from app.schemas import ComplaintResponse
    
    db = SessionLocal()
    try:
        complaints = db.query(Complaint).all()
        print(f"Total complaints found for validation: {len(complaints)}")
        
        for comp in complaints:
            # Construct a ComplaintResponse via Pydantic model_validate.
            # This triggers all validations including Pydantic string enums and JSON structures.
            try:
                # model_validate will fail loudly on ValidationError
                validated = ComplaintResponse.model_validate(comp)
                print(f"  [Validated Row ID {validated.id}]: OK (Type={validated.complaintType.value}, Lang={validated.originalLanguage.value})")
            except Exception as val_err:
                print(f"\nCRITICAL: Post-migration validation failed on row ID {comp.id}!")
                print(f"Row data: complaintType={comp.complaintType}, originalLanguage={comp.originalLanguage}, translatedText={comp.translatedText}")
                raise val_err
                
        print("POST-MIGRATION VALIDATION COMPLETED SUCCESSFULLY. ALL ROWS COMPLY.")
    finally:
        db.close()

if __name__ == "__main__":
    run_db_schema_migration()
    run_post_migration_validation()
