from pathlib import Path
import sqlite3
from datetime import datetime

from flask import Flask, flash, g, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "hospital.db"

app = Flask(__name__)
app.config["DATABASE"] = DATABASE
app.config["SECRET_KEY"] = "hospital-management-local"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_database():
    if DATABASE.exists():
        db = sqlite3.connect(DATABASE)
        try:
            columns = [row[1] for row in db.execute('PRAGMA table_info("MedicineGiven")')]
            if columns and "ID" not in columns:
                db.execute('DROP TRIGGER IF EXISTS "MedicineTrigger"')
                db.execute('DROP TABLE IF EXISTS "MedicineGiven_new"')
                db.execute('''CREATE TABLE "MedicineGiven_new" (
                    "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
                    "PatientID" INTEGER NOT NULL,
                    "Diagnosis" TEXT,
                    "Medicine" TEXT,
                    "DateTime" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )''')
                db.execute('''INSERT INTO "MedicineGiven_new" ("PatientID", "Diagnosis", "Medicine", "DateTime")
                              SELECT "PatientID", "Diagnosis", "Medicine", "DateTime" FROM "MedicineGiven"''')
                db.execute('DROP TABLE "MedicineGiven"')
                db.execute('ALTER TABLE "MedicineGiven_new" RENAME TO "MedicineGiven"')
                db.execute('''CREATE TRIGGER "MedicineTrigger"
                              AFTER INSERT ON "Consultation"
                              FOR EACH ROW
                              BEGIN
                                  INSERT INTO "MedicineGiven" ("PatientID", "Diagnosis", "Medicine", "DateTime")
                                  VALUES (NEW.PatientID, NEW.Diagnosis, NEW.Medicine, NEW.DateTime);
                              END''')
                db.commit()
        finally:
            db.close()
        return
    db = sqlite3.connect(DATABASE)
    try:
        for filename in ("init.sql", "views.sql", "triggers.sql"):
            db.executescript((BASE_DIR / filename).read_text())
        db.commit()
    finally:
        db.close()


def fetch_all(query, parameters=()):
    return get_db().execute(query, parameters).fetchall()


def fetch_one(query, parameters=()):
    return get_db().execute(query, parameters).fetchone()


def save_record(query, parameters):
    try:
        db = get_db()
        db.execute(query, parameters)
        db.commit()
    except sqlite3.IntegrityError as error:
        get_db().rollback()
        message = str(error)
        if "UNIQUE constraint failed" in message:
            message = "That email, phone number, or department already exists."
        elif "FOREIGN KEY constraint failed" in message:
            message = "Choose a valid related record before saving."
        elif "Payment cannot be processed" in message:
            message = "Billing amounts must be below 10,000."
        elif "CHECK constraint failed" in message:
            message = "One of the entered values is outside the allowed range."
        flash(message, "error")
        return False
    return True


@app.context_processor
def inject_navigation_counts():
    return {
        "now": datetime.now,
        "nav_counts": {
            "patients": fetch_one('SELECT COUNT(*) AS count FROM "Patient"')["count"],
            "doctors": fetch_one('SELECT COUNT(*) AS count FROM "Doctor"')["count"],
            "consultations": fetch_one('SELECT COUNT(*) AS count FROM "Consultation"')["count"],
        }
    }


@app.route("/")
def dashboard():
    stats = {
        "patients": fetch_one('SELECT COUNT(*) AS count FROM "Patient"')["count"],
        "doctors": fetch_one('SELECT COUNT(*) AS count FROM "Doctor"')["count"],
        "consultations": fetch_one('SELECT COUNT(*) AS count FROM "Consultation"')["count"],
        "billing": fetch_one('SELECT COUNT(*) AS count FROM "Billing"')["count"],
    }
    recent = fetch_all(
        '''SELECT c."ID", c."DateTime", c."Diagnosis", p."Name" AS patient,
                  d."Name" AS doctor
           FROM "Consultation" c
           JOIN "Patient" p ON p."ID" = c."PatientID"
           JOIN "Doctor" d ON d."ID" = c."DoctorID"
           ORDER BY c."ID" DESC LIMIT 6'''
    )
    return render_template("dashboard.html", stats=stats, recent=recent)


@app.route("/patients")
def patients():
    search = request.args.get("q", "").strip()
    like = f"%{search}%"
    records = fetch_all(
        '''SELECT * FROM "PatientWithAge"
           WHERE "Name" LIKE ? OR "PhoneNo" LIKE ? OR "City" LIKE ?
           ORDER BY "ID" DESC''',
        (like, like, like),
    )
    return render_template("patients.html", records=records, search=search)


@app.route("/patients/new", methods=("GET", "POST"))
def new_patient():
    if request.method == "POST":
        data = request.form
        if save_record(
            '''INSERT INTO "Patient" ("Name", "City", "PhoneNo", "Street", "Pincode", "birthdate")
               VALUES (?, ?, ?, ?, ?, ?)''',
            (data["name"], data["city"], data["phone"], data["street"], data["pincode"], data["birthdate"] or None),
        ):
            flash("Patient record added.", "success")
            return redirect(url_for("patients"))
    return render_template("patient_form.html")


@app.route("/doctors")
def doctors():
    records = fetch_all(
        '''SELECT d.*, dept."Name" AS department_name
           FROM "Doctor" d LEFT JOIN "Department" dept ON dept."ID" = d."Department"
           ORDER BY d."ID" DESC'''
    )
    return render_template("doctors.html", records=records)


@app.route("/doctors/new", methods=("GET", "POST"))
def new_doctor():
    departments = fetch_all('SELECT "ID", "Name" FROM "Department" ORDER BY "Name"')
    if request.method == "POST":
        data = request.form
        if save_record(
            '''INSERT INTO "Doctor" ("Name", "Type", "Email", "PhoneNo", "birthdate", "Department", "Salary")
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (data["name"], data["type"], data["email"], data["phone"], data["birthdate"] or None,
             data["department"] or None, data["salary"] or 10000),
        ):
            flash("Doctor record added.", "success")
            return redirect(url_for("doctors"))
    return render_template("doctor_form.html", departments=departments)


@app.route("/consultations")
def consultations():
    records = fetch_all(
        '''SELECT c.*, p."Name" AS patient, d."Name" AS doctor
           FROM "Consultation" c
           JOIN "Patient" p ON p."ID" = c."PatientID"
           JOIN "Doctor" d ON d."ID" = c."DoctorID"
           ORDER BY c."ID" DESC'''
    )
    return render_template("consultations.html", records=records)


@app.route("/consultations/new", methods=("GET", "POST"))
def new_consultation():
    patients_list = fetch_all('SELECT "ID", "Name", "PhoneNo" FROM "Patient" ORDER BY "Name"')
    doctors_list = fetch_all('SELECT "ID", "Name", "Type" FROM "Doctor" ORDER BY "Name"')
    if request.method == "POST":
        data = request.form
        if save_record(
            '''INSERT INTO "Consultation" ("PatientID", "DoctorID", "Diagnosis", "Medicine", "TestType")
               VALUES (?, ?, ?, ?, ?)''',
            (data["patient_id"], data["doctor_id"], data["diagnosis"], data["medicine"], data["test_type"] or None),
        ):
            flash("Consultation recorded.", "success")
            return redirect(url_for("consultations"))
    return render_template("consultation_form.html", patients=patients_list, doctors=doctors_list)


@app.route("/billing")
def billing():
    records = fetch_all(
        '''SELECT b.*, p."Name" AS patient, d."Name" AS doctor
           FROM "Billing" b
           LEFT JOIN "Consultation" c ON c."ID" = b."ConsultationID"
           LEFT JOIN "Patient" p ON p."ID" = c."PatientID"
           LEFT JOIN "Doctor" d ON d."ID" = b."DoctorID"
           ORDER BY b."TransactionID" DESC'''
    )
    return render_template("billing.html", records=records)


@app.route("/billing/new", methods=("GET", "POST"))
def new_billing():
    consultations_list = fetch_all(
        '''SELECT c."ID", c."DateTime", p."Name" AS patient, d."Name" AS doctor
           FROM "Consultation" c JOIN "Patient" p ON p."ID" = c."PatientID"
           JOIN "Doctor" d ON d."ID" = c."DoctorID" ORDER BY c."ID" DESC'''
    )
    if request.method == "POST":
        data = request.form
        doctor_id = fetch_one('SELECT "DoctorID" FROM "Consultation" WHERE "ID" = ?', (data["consultation_id"],))["DoctorID"]
        if save_record(
            '''INSERT INTO "Billing" ("ConsultationID", "DoctorID", "Amount") VALUES (?, ?, ?)''',
            (data["consultation_id"], doctor_id, data["amount"]),
        ):
            flash("Payment recorded.", "success")
            return redirect(url_for("billing"))
    return render_template("billing_form.html", consultations=consultations_list)


ensure_database()


if __name__ == "__main__":
    app.run(debug=True)