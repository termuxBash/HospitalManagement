from pathlib import Path
import sqlite3
import json
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation

from flask import Flask, flash, g, redirect, render_template, request, session, url_for


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "database_config.json"
DEFAULT_DATABASE_NAME = "hospital.db"
LOGIN_USERNAME = "hospital"
LOGIN_PASSWORD = "hospital123"

app = Flask(__name__)
app.config["DATABASE"] = BASE_DIR / DEFAULT_DATABASE_NAME
app.config["SECRET_KEY"] = "hospital-management-local"

DEFAULT_BIRTHDATE = "2003-10-24"


def _text(value, minimum=1, maximum=120):
    length = len(value.strip())
    return minimum <= length <= maximum


def _phone(value):
    return re.fullmatch(r"[0-9]{10}", value) is not None


def _integer(value, minimum, maximum):
    return re.fullmatch(r"[0-9]+", value) is not None and minimum <= int(value) <= maximum


def _birthdate(value):
    if not value:
        return True
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return parsed.isoformat() == value and parsed <= datetime.now().date()
    except ValueError:
        return False


def _email(value):
    return (
        len(value) <= 254
        and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) is not None
    )


def _amount(value):
    try:
        amount = Decimal(value)
        return amount.is_finite() and Decimal("0") < amount < Decimal("10000")
    except (InvalidOperation, ValueError):
        return False


def _record_exists(table, value):
    queries = {
        "Patient": 'SELECT 1 FROM "Patient" WHERE "ID" = ?',
        "Doctor": 'SELECT 1 FROM "Doctor" WHERE "ID" = ?',
        "Consultation": 'SELECT 1 FROM "Consultation" WHERE "ID" = ?',
        "Department": 'SELECT 1 FROM "Department" WHERE "ID" = ?',
    }
    return table in queries and fetch_one(queries[table], (value,)) is not None


POST_RULES = {
    "login": {
        "username": (True, lambda v: _text(v, 1, 80), "Enter a valid username."),
        "password": (True, lambda v: _text(v, 1, 200), "Enter a valid password."),
    },
    "new_patient": {
        "name": (True, lambda v: _text(v, 2, 120), "Name must be 2–120 characters."),
        "phone": (True, _phone, "Phone number must contain exactly 10 digits."),
        "city": (True, lambda v: _text(v, 1, 100), "Enter a valid city."),
        "pincode": (True, lambda v: re.fullmatch(r"[0-9]{4,10}", v) is not None,
                    "Postal code must contain 4–10 digits."),
        "street": (False, lambda v: _text(v, 0, 200),
                   "Street address must be at most 200 characters."),
        "birthdate": (False, _birthdate,
                      "Birth date must be valid and cannot be in the future."),
    },
    "new_doctor": {
        "name": (True, lambda v: _text(v, 2, 120), "Name must be 2–120 characters."),
        "type": (True, lambda v: v in {"Consultant", "Specialist", "Surgeon", "Resident"},
                 "Choose a valid role."),
        "email": (True, _email, "Enter a valid email address."),
        "phone": (True, _phone, "Phone number must contain exactly 10 digits."),
        "birthdate": (False, _birthdate,
                      "Birth date must be valid and cannot be in the future."),
        "department": (
            False,
            lambda v: not v or (
                _integer(v, 1, 2147483647) and _record_exists("Department", v)
            ),
            "Choose a valid department.",
        ),
        "salary": (True, lambda v: _integer(v, 1001, 10000000),
                   "Salary must be between 1,001 and 10,000,000."),
    },
    "new_consultation": {
        "patient_id": (
            True,
            lambda v: _integer(v, 1, 2147483647) and _record_exists("Patient", v),
            "Choose a valid patient.",
        ),
        "doctor_id": (
            True,
            lambda v: _integer(v, 1, 2147483647) and _record_exists("Doctor", v),
            "Choose a valid doctor.",
        ),
        "diagnosis": (False, lambda v: _text(v, 0, 500),
                      "Diagnosis must be at most 500 characters."),
        "medicine": (False, lambda v: _text(v, 0, 500),
                     "Medicine must be at most 500 characters."),
        "test_type": (False, lambda v: not v or _integer(v, 1, 999999),
                      "Test code must be a positive number."),
    },
    "new_billing": {
        "consultation_id": (
            True,
            lambda v: _integer(v, 1, 2147483647) and _record_exists("Consultation", v),
            "Choose a valid consultation.",
        ),
        "amount": (True, _amount,
                   "Amount must be greater than 0 and below 10,000."),
    },
    "new_department": {
        "name": (True, lambda v: _text(v, 2, 80),
                 "Department name must be 2–80 characters."),
    },
    "database_settings": {
        "database_name": (
            True,
            lambda v: len(v) <= 255
            and re.fullmatch(r"[^/\\\\]+\\.(?:db|sqlite|sqlite3)", v) is not None,
            "Use a local filename ending in .db, .sqlite, or .sqlite3.",
        ),
    },
}

@app.before_request
def require_login():
    public_endpoints = {"login", "static"}
    if request.endpoint not in public_endpoints and not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        validation_endpoint = {
            "edit_patient": "new_patient",
            "edit_doctor": "new_doctor",
            "edit_consultation": "new_consultation",
        }.get(request.endpoint, request.endpoint)
        rules = POST_RULES.get(validation_endpoint, {})
        for field, (required, validator, message) in rules.items():
            value = request.form.get(field, "").strip()
            if (required and not value) or (value and not validator(value)):
                flash(message, "error")
                form_pages = {
                    "login": "login",
                    "new_patient": "new_patient",
                    "new_doctor": "new_doctor",
                    "new_consultation": "new_consultation",
                    "new_billing": "new_billing",
                    "new_department": "new_department",
                    "database_settings": "database_settings",
                }
                if request.endpoint.startswith("edit_"):
                    return redirect(url_for(request.endpoint, **request.view_args))
                return redirect(url_for(form_pages[validation_endpoint]))


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        if (request.form.get("username") == LOGIN_USERNAME and
                request.form.get("password") == LOGIN_PASSWORD):
            session.clear()
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def read_database_name():
    try:
        name = json.loads(CONFIG_FILE.read_text()).get("database_name", DEFAULT_DATABASE_NAME)
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        name = DEFAULT_DATABASE_NAME
    path = Path(str(name)).name
    return path if path.endswith((".db", ".sqlite", ".sqlite3")) else DEFAULT_DATABASE_NAME


def set_database_name(name):
    safe_name = Path(name).name
    if safe_name != name or not safe_name.endswith((".db", ".sqlite", ".sqlite3")):
        raise ValueError("Database name must be a local .db, .sqlite, or .sqlite3 file.")
    CONFIG_FILE.write_text(json.dumps({"database_name": safe_name}, indent=2) + "\n")
    app.config["DATABASE"] = BASE_DIR / safe_name


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
    database = app.config["DATABASE"]
    db = sqlite3.connect(database)
    try:
        db.execute("PRAGMA foreign_keys = ON")
        existing_tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
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
        if not existing_tables:
            db.executescript((BASE_DIR / "init.sql").read_text())
            db.executescript((BASE_DIR / "views.sql").read_text())
            db.executescript((BASE_DIR / "triggers.sql").read_text())
        elif "BillingAudit" not in existing_tables:
            db.executescript('''CREATE TABLE "BillingAudit" (
                "AuditID" INTEGER PRIMARY KEY AUTOINCREMENT,
                "TransactionID" INTEGER,
                "Action" TEXT NOT NULL CHECK("Action" IN ('INSERT', 'UPDATE', 'DELETE')),
                "OldAmount" NUMERIC,
                "NewAmount" NUMERIC,
                "OldConsultationID" INTEGER,
                "NewConsultationID" INTEGER,
                "OldDoctorID" INTEGER,
                "NewDoctorID" INTEGER,
                "ChangedAt" TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )''')
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
        elif "CHECK constraint failed" in message and ("Billing" in message or "Amount" in message):
            message = "Billing amounts must be greater than zero and below 10,000."
        elif "CHECK constraint failed" in message:
            message = "One of the entered values is outside the allowed range."
        flash(message, "error")
        return False
    return True


def grouped_by_patient(records):
    groups = []
    by_patient = {}
    for record in records:
        patient = record["patient"] or "Unlinked patient"
        if patient not in by_patient:
            by_patient[patient] = {"patient": patient, "records": []}
            groups.append(by_patient[patient])
        by_patient[patient]["records"].append(record)
    return groups


@app.context_processor
def inject_navigation_counts():
    return {
        "now": datetime.now,
        "database_name": Path(app.config["DATABASE"]).name,
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
            (data["name"], data["city"], data["phone"], data["street"], data["pincode"],
 data["birthdate"] or DEFAULT_BIRTHDATE),
        ):
            flash("Patient record added.", "success")
            return redirect(url_for("patients"))
    return render_template("patient_form.html")


@app.route("/patients/<int:patient_id>/edit", methods=("GET", "POST"))
def edit_patient(patient_id):
    record = fetch_one('SELECT * FROM "Patient" WHERE "ID" = ?', (patient_id,))
    if record is None:
        flash("Patient record not found.", "error")
        return redirect(url_for("patients"))
    if request.method == "POST":
        data = request.form
        if save_record(
            '''UPDATE "Patient" SET "Name" = ?, "City" = ?, "PhoneNo" = ?,
               "Street" = ?, "Pincode" = ?, "birthdate" = ? WHERE "ID" = ?''',
            (data["name"], data["city"], data["phone"], data["street"], data["pincode"],
             data["birthdate"] or DEFAULT_BIRTHDATE, patient_id),
        ):
            flash("Patient record updated.", "success")
            return redirect(url_for("patients"))
    return render_template("patient_form.html", record=record, editing=True)


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
            (data["name"], data["type"], data["email"], data["phone"],
 data["birthdate"] or DEFAULT_BIRTHDATE, data["department"] or None,
 data["salary"] or 10000),
        ):
            flash("Doctor record added.", "success")
            return redirect(url_for("doctors"))
    return render_template("doctor_form.html", departments=departments)


@app.route("/doctors/<int:doctor_id>/edit", methods=("GET", "POST"))
def edit_doctor(doctor_id):
    record = fetch_one('SELECT * FROM "Doctor" WHERE "ID" = ?', (doctor_id,))
    departments = fetch_all('SELECT "ID", "Name" FROM "Department" ORDER BY "Name"')
    if record is None:
        flash("Doctor record not found.", "error")
        return redirect(url_for("doctors"))
    if request.method == "POST":
        data = request.form
        if save_record(
            '''UPDATE "Doctor" SET "Name" = ?, "Type" = ?, "Email" = ?, "PhoneNo" = ?,
               "birthdate" = ?, "Department" = ?, "Salary" = ? WHERE "ID" = ?''',
            (data["name"], data["type"], data["email"], data["phone"],
             data["birthdate"] or DEFAULT_BIRTHDATE, data["department"] or None,
             data["salary"] or 10000, doctor_id),
        ):
            flash("Doctor record updated.", "success")
            return redirect(url_for("doctors"))
    return render_template("doctor_form.html", departments=departments, record=record, editing=True)


@app.route("/consultations")
def consultations():
    records = fetch_all(
        '''SELECT c.*, p."Name" AS patient, d."Name" AS doctor
           FROM "Consultation" c
           JOIN "Patient" p ON p."ID" = c."PatientID"
           JOIN "Doctor" d ON d."ID" = c."DoctorID"
           ORDER BY p."Name", c."ID" DESC'''
    )
    return render_template("consultations.html", groups=grouped_by_patient(records))


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


@app.route("/consultations/<int:consultation_id>/edit", methods=("GET", "POST"))
def edit_consultation(consultation_id):
    record = fetch_one('SELECT * FROM "Consultation" WHERE "ID" = ?', (consultation_id,))
    patients_list = fetch_all('SELECT "ID", "Name", "PhoneNo" FROM "Patient" ORDER BY "Name"')
    doctors_list = fetch_all('SELECT "ID", "Name", "Type" FROM "Doctor" ORDER BY "Name"')
    if record is None:
        flash("Consultation record not found.", "error")
        return redirect(url_for("consultations"))
    if request.method == "POST":
        data = request.form
        if save_record(
            '''UPDATE "Consultation" SET "PatientID" = ?, "DoctorID" = ?, "Diagnosis" = ?,
               "Medicine" = ?, "TestType" = ? WHERE "ID" = ?''',
            (data["patient_id"], data["doctor_id"], data["diagnosis"], data["medicine"],
             data["test_type"] or None, consultation_id),
        ):
            flash("Consultation updated.", "success")
            return redirect(url_for("consultations"))
    return render_template("consultation_form.html", patients=patients_list, doctors=doctors_list,
                           record=record, editing=True)


@app.route("/billing")
def billing():
    records = fetch_all(
        '''SELECT b.*, p."Name" AS patient, d."Name" AS doctor
           FROM "Billing" b
           LEFT JOIN "Consultation" c ON c."ID" = b."ConsultationID"
           LEFT JOIN "Patient" p ON p."ID" = c."PatientID"
           LEFT JOIN "Doctor" d ON d."ID" = b."DoctorID"
           ORDER BY p."Name", b."TransactionID" DESC'''
    )
    return render_template("billing.html", groups=grouped_by_patient(records))


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


@app.route("/billing/audit")
def billing_audit():
    records = fetch_all(
        '''SELECT a.*, COALESCE(p_new."Name", p_old."Name") AS patient
           FROM "BillingAudit" a
           LEFT JOIN "Consultation" c_new ON c_new."ID" = a."NewConsultationID"
           LEFT JOIN "Patient" p_new ON p_new."ID" = c_new."PatientID"
           LEFT JOIN "Consultation" c_old ON c_old."ID" = a."OldConsultationID"
           LEFT JOIN "Patient" p_old ON p_old."ID" = c_old."PatientID"
           ORDER BY patient, a."AuditID" DESC'''
    )
    return render_template("billing_audit.html", groups=grouped_by_patient(records))


@app.route("/settings/database", methods=("GET", "POST"))
def database_settings():
    if request.method == "POST":
        try:
            set_database_name(request.form["database_name"].strip())
            ensure_database()
            flash(f"Using database {Path(app.config['DATABASE']).name}.", "success")
            return redirect(url_for("dashboard"))
        except (KeyError, ValueError, OSError, sqlite3.Error) as error:
            flash(str(error), "error")
    return render_template("database_settings.html", database_name=Path(app.config["DATABASE"]).name)


@app.route("/departments")
def departments():
    records = fetch_all('SELECT "ID", "Name" FROM "Department" ORDER BY "Name"')
    return render_template("departments.html", records=records)


@app.route("/departments/new", methods=("GET", "POST"))
def new_department():
    if request.method == "POST":
        if save_record(
            'INSERT INTO "Department" ("Name") VALUES (?)',
            (request.form["name"].strip(),),
        ):
            flash("Department added.", "success")
            return redirect(url_for("departments"))
    return render_template("department_form.html")


set_database_name(read_database_name())
ensure_database()


if __name__ == "__main__":
    app.run(debug=True)