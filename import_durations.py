# import_durations.py
"""
Usage:
1) Ensure files exist in same folder:
   - serviceAccountKey.json
   - durations.xlsx
2) Install dependencies:
      pip install -r requirements.txt
3) Run:
      python import_durations.py
"""

import sys
import re
import pandas as pd
from firebase_admin import credentials, initialize_app, firestore

# ===== CONFIG =====
EXCEL_PATH = "durations.xlsx"
SHEET_NAME = 0
COLLECTION = "durations_table"
DOC_ID_REPLACE = {"/": "|", "\\": "|"}
# ==================

def normalize_doc_id(text: str) -> str:
    """Make LOV_TYPE safe to use as Firestore document ID."""
    s = str(text).strip()
    for bad, good in DOC_ID_REPLACE.items():
        s = s.replace(bad, good)
    s = re.sub(r"\s+", " ", s)
    return s

def to_bool(x):
    """Convert T/F or True/False or 1/0 to boolean."""
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    if s in ("t", "true", "1", "yes", "y"):
        return True
    if s in ("f", "false", "0", "no", "n"):
        return False
    return False

def main():
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
        initialize_app(cred)
    except ValueError:
        pass  # Already initialized
    
    db = firestore.client()

    # Read Excel
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    except Exception as e:
        print(f"[ERROR] Cannot read Excel file: {e}")
        sys.exit(1)

    # Required columns
    required_columns = {"LOV_TYPE", "DEADLINE_DAYS", "START_SAME_DAY"}
    if not required_columns.issubset(df.columns):
        print("[ERROR] Excel missing required columns:", required_columns)
        print("Columns found:", list(df.columns))
        sys.exit(1)

    df["LOV_TYPE"] = df["LOV_TYPE"].astype(str).str.strip()
    df["DEADLINE_DAYS"] = pd.to_numeric(df["DEADLINE_DAYS"], errors="coerce").fillna(0).astype(int)
    df["START_SAME_DAY"] = df["START_SAME_DAY"].apply(to_bool)

    df = df[df["LOV_TYPE"].str.len() > 0]

    batch = db.batch()
    count = 0

    for _, row in df.iterrows():
        lov_type = row["LOV_TYPE"]
        doc_id = normalize_doc_id(lov_type)
        doc_ref = db.collection(COLLECTION).document(doc_id)

        data = {
            "lov_type": lov_type,
            "deadline_days": int(row["DEADLINE_DAYS"]),
            "start_same_day": bool(row["START_SAME_DAY"]),
            "is_active": True
        }

        batch.set(doc_ref, data)
        count += 1
        
        if count % 450 == 0:
            batch.commit()
            batch = db.batch()

    batch.commit()

    print(f"[✅] Successfully uploaded {count} records to '{COLLECTION}'!")
    print(df.head())

if __name__ == "__main__":
    main()
