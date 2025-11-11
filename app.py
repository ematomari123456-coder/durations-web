from flask import Flask, render_template, request
from firebase_admin import credentials, initialize_app, firestore
from datetime import datetime, timedelta, date

# ========== FIREBASE INIT ==========
cred = credentials.Certificate("serviceAccountKey.json")
try:
    initialize_app(cred)
except:
    pass

db = firestore.client()
COLLECTION = "durations_table"

# ========== FLASK APP ==========
app = Flask(__name__)

# ========== CONSTANTS ==========
WEEKENDS = [4, 5]  # Friday=4, Saturday=5 (weekday: Monday=0)

# ========== FUNCTIONS ==========

def calculate(judgment_date, deadline_days, start_same_day):
    # 1) Start date
    if start_same_day:
        start_date = judgment_date
    else:
        start_date = judgment_date + timedelta(days=1)

    # 2) Preliminary end date
    end_date = start_date + timedelta(days=deadline_days - 1)

    # 3) Extend if weekend
    extended = False
    while end_date.weekday() in WEEKENDS:
        end_date = end_date + timedelta(days=1)
        extended = True

    # 4) Remaining days
    today = date.today()

    if today > end_date:
        rem = 0
    else:
        rem = (end_date - today).days
        if start_same_day:
            rem += 1

    highlight = (0 < rem <= 5)

    return start_date, end_date, rem, highlight, extended

# ========== ROUTES ==========

@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    # fetch LOV list with doc IDs
    docs = db.collection(COLLECTION).where("is_active", "==", True).stream()
    lov_list = [{"id": doc.id, **doc.to_dict()} for doc in docs]

    if request.method == "POST":
        doc_id = request.form.get("lov_type")  # <-- ID not text
        jd = request.form.get("judgment_date")

        if not doc_id or not jd:
            return render_template("index.html", lov_list=lov_list, result="missing")

        # get record by document ID
        record = db.collection(COLLECTION).document(doc_id).get()
        data = record.to_dict()

        # read values
        deadline_days = data['deadline_days']
        start_same_day = data['start_same_day']
        judgment_date = datetime.strptime(jd, "%Y-%m-%d").date()

        start_date, end_date, rem, highlight, extended = calculate(
            judgment_date, deadline_days, start_same_day
        )

        result = {
            "lov_type": data["lov_type"],
            "start_date": start_date,
            "end_date": end_date,
            "remaining_days": rem,
            "highlight": highlight,
            "extended": extended
        }

    return render_template("index.html", lov_list=lov_list, result=result)

# ========== RUN APP ==========
if __name__ == "__main__":
    app.run(debug=True)
