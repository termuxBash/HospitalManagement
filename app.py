from pathlib import Path
import sqlite3
import json
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    pymysql = None

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


class DictRow(dict):
    """Dictionary supporting integer indexing (like sqlite3.Row) and dict keys."""
    def __init__(self, mapping=None, **kwargs):
        data = {}
        if mapping:
            for k, v in mapping.items():
                if hasattr(v, "isoformat"):
                    data[k] = v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "hour") else v.strftime("%Y-%m-%d")
                else:
                    data[k] = v
        super().__init__(data, **kwargs)
        self._keys = list(self.keys())

    def __getitem__(self, item):
        if isinstance(item, int):
            return super().__getitem__(self._keys[item])
        return super().__getitem__(item)


def read_database_config():
    default_config = {
        "db_type": "mysql",
        "database_name": DEFAULT_DATABASE_NAME,
        "mysql": {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "hospital",
            "unix_socket": "",
        },
    }
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text())
            default_config.update(cfg)
    except Exception:
        pass
    return default_config


def save_database_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def is_mysql():
    return read_database_config().get("db_type", "mysql") == "mysql"


def ensure_mysqld_running():
    socket_path = "/tmp/mysql.sock"
    datadir = Path("/tmp/mysql_data")
    if pymysql is None:
        return False

    def _setup_users(conn):
        try:
            import getpass
            cfg = read_database_config().get("mysql", {})
            configured_user = cfg.get("user") or getpass.getuser()
            with conn.cursor() as cur:
                cur.execute("CREATE DATABASE IF NOT EXISTS hospital")
                if configured_user and configured_user != "root":
                    cur.execute(f"CREATE USER IF NOT EXISTS '{configured_user}'@'localhost' IDENTIFIED BY ''")
                    cur.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{configured_user}'@'localhost' WITH GRANT OPTION")
                    cur.execute("FLUSH PRIVILEGES")
        except Exception:
            pass

    try:
        test_conn = pymysql.connect(unix_socket=socket_path, user="root", connect_timeout=1)
        _setup_users(test_conn)
        test_conn.close()
        return True
    except Exception:
        pass

    import subprocess
    if not datadir.exists() or not (datadir / "mysql").exists():
        import shutil
        if datadir.exists():
            shutil.rmtree(datadir, ignore_errors=True)
        datadir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["/usr/sbin/mysqld", "--no-defaults", "--initialize-insecure", f"--datadir={datadir}"],
                check=True,
                capture_output=True,
                timeout=30,
            )
        except Exception:
            pass

    try:
        subprocess.Popen(
            [
                "/usr/sbin/mysqld",
                "--no-defaults",
                f"--datadir={datadir}",
                f"--socket={socket_path}",
                "--port=3307",
                "--bind-address=127.0.0.1",
                "--mysqlx=OFF",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import time
        for _ in range(10):
            time.sleep(0.5)
            try:
                test_conn = pymysql.connect(unix_socket=socket_path, user="root", connect_timeout=1)
                _setup_users(test_conn)
                test_conn.close()
                return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def get_mysql_params():
    cfg = read_database_config().get("mysql", {})
    socket_path = cfg.get("unix_socket")

    # If socket_path is not explicitly provided, auto-detect working socket
    # Prioritizing /tmp/mysql.sock which runs without password for local development
    if not socket_path:
        ensure_mysqld_running()
        for candidate in ["/tmp/mysql.sock", "/var/run/mysqld/mysqld.sock"]:
            if Path(candidate).exists():
                try:
                    test_conn = pymysql.connect(
                        unix_socket=candidate,
                        user=cfg.get("user", "root"),
                        password=cfg.get("password", ""),
                        connect_timeout=1,
                    )
                    test_conn.close()
                    socket_path = candidate
                    break
                except Exception:
                    pass
        if not socket_path and Path("/tmp/mysql.sock").exists():
            socket_path = "/tmp/mysql.sock"
    elif socket_path == "/tmp/mysql.sock":
        ensure_mysqld_running()

    params = {
        "user": cfg.get("user", "root"),
        "password": cfg.get("password", ""),
        "database": cfg.get("database", "hospital"),
        "charset": "utf8mb4",
        "autocommit": False,
        "cursorclass": pymysql.cursors.DictCursor,
    }
    if socket_path and Path(socket_path).exists():
        params["unix_socket"] = socket_path
    else:
        params["host"] = cfg.get("host", "127.0.0.1")
        params["port"] = int(cfg.get("port", 3306))
    return params


def get_active_database_label():
    cfg = read_database_config()
    if cfg.get("db_type") == "mysql":
        mcfg = cfg.get("mysql", {})
        return f"MySQL ({mcfg.get('database', 'hospital')})"
    return f"SQLite ({Path(cfg.get('database_name', DEFAULT_DATABASE_NAME)).name})"


def set_database_name(name):
    safe_name = Path(name).name
    if safe_name != name or not safe_name.endswith((".db", ".sqlite", ".sqlite3")):
        raise ValueError("Database name must be a local .db, .sqlite, or .sqlite3 file.")
    cfg = read_database_config()
    cfg["database_name"] = safe_name
    save_database_config(cfg)
    app.config["DATABASE"] = BASE_DIR / safe_name


def get_db():
    if "db" not in g:
        if is_mysql():
            if pymysql is None:
                raise RuntimeError("PyMySQL package is not installed. Please install it using: pip install pymysql")
            params = get_mysql_params()
            conn = pymysql.connect(**params)
            with conn.cursor() as cur:
                cur.execute("SET SESSION sql_mode = 'ANSI_QUOTES,STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
            g.db = conn
            g.is_mysql = True
        else:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
            g.is_mysql = False
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_database():
    cfg = read_database_config()
    if is_mysql():
        if pymysql is None:
            return
        mcfg = cfg.get("mysql", {})
        db_name = mcfg.get("database", "hospital")
        # Ensure database exists
        params_nodb = get_mysql_params()
        params_nodb.pop("database", None)
        try:
            conn_temp = pymysql.connect(**params_nodb)
            with conn_temp.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
            conn_temp.close()
        except Exception:
            pass

        conn = pymysql.connect(**get_mysql_params())
        try:
            with conn.cursor() as cur:
                cur.execute("SET SESSION sql_mode = 'ANSI_QUOTES,STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
                cur.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s", (db_name,))
                existing_tables = {row["TABLE_NAME"] if isinstance(row, dict) else row[0] for row in cur.fetchall()}

                if "Doctor" not in existing_tables or "Patient" not in existing_tables:
                    init_sql = (BASE_DIR / "init_mysql.sql").read_text()
                    for stmt in init_sql.split(";"):
                        stmt = stmt.strip()
                        if stmt:
                            cur.execute(stmt)

                    views_sql = (BASE_DIR / "views_mysql.sql").read_text()
                    for stmt in views_sql.split(";"):
                        stmt = stmt.strip()
                        if stmt:
                            cur.execute(stmt)

                    triggers = [
                        ("BillingInsertAudit", """
                        CREATE TRIGGER BillingInsertAudit AFTER INSERT ON Billing FOR EACH ROW
                        BEGIN
                            INSERT INTO BillingAudit (TransactionID, Action, NewAmount, NewConsultationID, NewDoctorID)
                            VALUES (NEW.TransactionID, 'INSERT', NEW.Amount, NEW.ConsultationID, NEW.DoctorID);
                        END
                        """),
                        ("BillingUpdateAudit", """
                        CREATE TRIGGER BillingUpdateAudit AFTER UPDATE ON Billing FOR EACH ROW
                        BEGIN
                            INSERT INTO BillingAudit (TransactionID, Action, OldAmount, NewAmount, OldConsultationID, NewConsultationID, OldDoctorID, NewDoctorID)
                            VALUES (NEW.TransactionID, 'UPDATE', OLD.Amount, NEW.Amount, OLD.ConsultationID, NEW.ConsultationID, OLD.DoctorID, NEW.DoctorID);
                        END
                        """),
                        ("BillingDeleteAudit", """
                        CREATE TRIGGER BillingDeleteAudit AFTER DELETE ON Billing FOR EACH ROW
                        BEGIN
                            INSERT INTO BillingAudit (TransactionID, Action, OldAmount, OldConsultationID, OldDoctorID)
                            VALUES (OLD.TransactionID, 'DELETE', OLD.Amount, OLD.ConsultationID, OLD.DoctorID);
                        END
                        """),
                        ("MedicineTrigger", """
                        CREATE TRIGGER MedicineTrigger AFTER INSERT ON Consultation FOR EACH ROW
                        BEGIN
                            INSERT INTO MedicineGiven (PatientID, Diagnosis, Medicine, DateTime)
                            VALUES (NEW.PatientID, NEW.Diagnosis, NEW.Medicine, NEW.DateTime);
                        END
                        """),
                    ]
                    for name, sql in triggers:
                        cur.execute(f"DROP TRIGGER IF EXISTS `{name}`")
                        cur.execute(sql)

                if "product" not in existing_tables:
                    cur.execute("""
                    CREATE TABLE IF NOT EXISTS product (
                        product_id INT PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        price INT,
                        qty INT,
                        description VARCHAR(255)
                    ) ENGINE=InnoDB;
                    """)
                    cur.execute("""
                    INSERT INTO product (product_id, name, price, qty, description) VALUES
                    (1, 'Ferrero', 500, 5, 'chocolate'),
                    (2, 'Kurkure', 50, 1, 'snacks'),
                    (3, 'lays', 120, 1, 'snacks'),
                    (4, 'thepla', 92, 8, 'snacks'),
                    (5, 'pickle', 300, 3, 'snacks'),
                    (6, 'dorritos', 2020, 2, 'snacks'),
                    (7, 'LogitechG650', 500, 2, 'Mouse')
                    ON DUPLICATE KEY UPDATE name=VALUES(name);
                    """)
            conn.commit()
        finally:
            conn.close()
    else:
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
    db = get_db()
    if is_mysql():
        query_sql = query.replace("?", "%s")
        with db.cursor() as cursor:
            cursor.execute(query_sql, parameters)
            rows = cursor.fetchall()
            return [DictRow(r) for r in rows]
    else:
        return db.execute(query, parameters).fetchall()


def fetch_one(query, parameters=()):
    db = get_db()
    if is_mysql():
        query_sql = query.replace("?", "%s")
        with db.cursor() as cursor:
            cursor.execute(query_sql, parameters)
            row = cursor.fetchone()
            return DictRow(row) if row is not None else None
    else:
        return db.execute(query, parameters).fetchone()


def save_record(query, parameters):
    db = get_db()
    try:
        if is_mysql():
            query_sql = query.replace("?", "%s")
            with db.cursor() as cursor:
                cursor.execute(query_sql, parameters)
            db.commit()
        else:
            db.execute(query, parameters)
            db.commit()
    except Exception as error:
        db.rollback()
        msg = str(error)
        code = getattr(error, "args", [None])[0]
        if code == 1062 or "Duplicate entry" in msg or "UNIQUE constraint failed" in msg:
            message = "That email, phone number, or department already exists."
        elif code == 1452 or "foreign key constraint fails" in msg.lower() or "FOREIGN KEY constraint failed" in msg:
            message = "Choose a valid related record before saving."
        elif (code == 3819 or "check constraint" in msg.lower() or "CHECK constraint failed" in msg) and (
            "amount" in msg.lower() or "billing" in msg.lower()
        ):
            message = "Billing amounts must be greater than zero and below 10,000."
        elif code == 3819 or "check constraint" in msg.lower() or "CHECK constraint failed" in msg:
            message = "One of the entered values is outside the allowed range."
        else:
            message = f"Database error: {error}"
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
    try:
        p_row = fetch_one('SELECT COUNT(*) AS count FROM "Patient"')
        d_row = fetch_one('SELECT COUNT(*) AS count FROM "Doctor"')
        c_row = fetch_one('SELECT COUNT(*) AS count FROM "Consultation"')
        patients_count = p_row["count"] if p_row else 0
        doctors_count = d_row["count"] if d_row else 0
        consultations_count = c_row["count"] if c_row else 0
    except Exception:
        patients_count, doctors_count, consultations_count = 0, 0, 0

    return {
        "now": datetime.now,
        "database_name": get_active_database_label(),
        "nav_counts": {
            "patients": patients_count,
            "doctors": doctors_count,
            "consultations": consultations_count,
        }
    }


if pymysql:
    @app.errorhandler(pymysql.Error)
    def handle_mysql_error(error):
        if request.endpoint == "database_settings":
            cfg = read_database_config()
            return render_template(
                "database_settings.html",
                db_type=cfg.get("db_type", "mysql"),
                mysql=cfg.get("mysql", {}),
                database_name=cfg.get("database_name", DEFAULT_DATABASE_NAME),
            )
        flash(f"Database error: {error}. You can verify or update database settings below.", "error")
        return redirect(url_for("database_settings"))


@app.route("/")
def dashboard():
    try:
        stats = {
            "patients": (fetch_one('SELECT COUNT(*) AS count FROM "Patient"') or {}).get("count", 0),
            "doctors": (fetch_one('SELECT COUNT(*) AS count FROM "Doctor"') or {}).get("count", 0),
            "consultations": (fetch_one('SELECT COUNT(*) AS count FROM "Consultation"') or {}).get("count", 0),
            "billing": (fetch_one('SELECT COUNT(*) AS count FROM "Billing"') or {}).get("count", 0),
        }
        recent = fetch_all(
            '''SELECT c."ID", c."DateTime", c."Diagnosis", p."Name" AS patient,
                  d."Name" AS doctor
           FROM "Consultation" c
           JOIN "Patient" p ON p."ID" = c."PatientID"
           JOIN "Doctor" d ON d."ID" = c."DoctorID"
           ORDER BY c."ID" DESC LIMIT 6'''
        )
    except Exception as error:
        flash(f"Could not connect to database: {error}. Please verify settings below.", "error")
        return redirect(url_for("database_settings"))
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
    cfg = read_database_config()
    if request.method == "POST":
        db_type = request.form.get("db_type", "mysql").strip()
        if db_type == "mysql":
            host = request.form.get("host", "localhost").strip()
            port_val = request.form.get("port", "3306").strip()
            port = int(port_val) if port_val.isdigit() else 3306
            user = request.form.get("user", "root").strip()
            password = request.form.get("password", "")
            database = request.form.get("database", "hospital").strip()
            unix_socket = request.form.get("unix_socket", "").strip()

            cfg["db_type"] = "mysql"
            cfg["mysql"] = {
                "host": host,
                "port": port,
                "user": user,
                "password": password,
                "database": database,
                "unix_socket": unix_socket,
            }
            save_database_config(cfg)
            try:
                ensure_database()
                flash(f"Connected to MySQL database '{database}'.", "success")
                return redirect(url_for("dashboard"))
            except Exception as error:
                flash(f"Error connecting to MySQL: {error}", "error")
        else:
            db_name = request.form.get("database_name", DEFAULT_DATABASE_NAME).strip()
            safe_name = Path(db_name).name
            if safe_name != db_name or not safe_name.endswith((".db", ".sqlite", ".sqlite3")):
                flash("Database name must be a local .db, .sqlite, or .sqlite3 file.", "error")
            else:
                cfg["db_type"] = "sqlite"
                cfg["database_name"] = safe_name
                save_database_config(cfg)
                app.config["DATABASE"] = BASE_DIR / safe_name
                try:
                    ensure_database()
                    flash(f"Using SQLite database '{safe_name}'.", "success")
                    return redirect(url_for("dashboard"))
                except Exception as error:
                    flash(f"Error configuring SQLite: {error}", "error")

    return render_template(
        "database_settings.html",
        db_type=cfg.get("db_type", "mysql"),
        mysql=cfg.get("mysql", {}),
        database_name=cfg.get("database_name", DEFAULT_DATABASE_NAME),
    )


@app.route("/access-control", methods=("GET", "POST"))
def access_control():
    if not is_mysql():
        return render_template("access_control.html", is_mysql=False, users=[])

    test_result = None
    test_params = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "create_user":
            username = request.form.get("username", "").strip()
            host = request.form.get("host", "localhost").strip() or "localhost"
            password = request.form.get("password", "")
            if not username or not re.match(r"^[A-Za-z0-9_]{1,32}$", username):
                flash("Username must contain 1–32 alphanumeric characters or underscores.", "error")
            else:
                try:
                    db = get_db()
                    with db.cursor() as cur:
                        cur.execute(f"CREATE USER IF NOT EXISTS '{username}'@'{host}' IDENTIFIED BY %s", (password,))
                        cur.execute("FLUSH PRIVILEGES")
                    db.commit()
                    flash(f"User '{username}'@'{host}' created successfully.", "success")
                except Exception as e:
                    flash(f"Error creating user: {e}", "error")

        elif action == "drop_user":
            username = request.form.get("username", "").strip()
            host = request.form.get("host", "localhost").strip() or "localhost"
            if username == "root":
                flash("Cannot drop root user.", "error")
            else:
                try:
                    db = get_db()
                    with db.cursor() as cur:
                        cur.execute(f"DROP USER IF EXISTS '{username}'@'{host}'")
                        cur.execute("FLUSH PRIVILEGES")
                    db.commit()
                    flash(f"User '{username}'@'{host}' deleted.", "success")
                except Exception as e:
                    flash(f"Error dropping user: {e}", "error")

        elif action == "modify_privilege":
            priv_action = request.form.get("priv_action", "GRANT")
            user_spec = request.form.get("user_spec", "")
            privilege = request.form.get("privilege", "SELECT")
            target = request.form.get("target", "hospital.product")

            if "@" in user_spec:
                user_part, host_part = user_spec.split("@", 1)
            else:
                user_part, host_part = user_spec, "localhost"

            allowed_privs = {"ALL PRIVILEGES", "INSERT", "SELECT", "UPDATE", "DELETE", "CREATE", "DROP"}
            if privilege not in allowed_privs:
                flash("Invalid privilege selected.", "error")
            else:
                try:
                    db = get_db()
                    with db.cursor() as cur:
                        if priv_action == "GRANT":
                            cur.execute(f"GRANT {privilege} ON {target} TO '{user_part}'@'{host_part}'")
                        else:  # REVOKE
                            if privilege == "ALL PRIVILEGES":
                                cur.execute(f"REVOKE ALL PRIVILEGES, GRANT OPTION FROM '{user_part}'@'{host_part}'")
                            else:
                                cur.execute(f"REVOKE {privilege} ON {target} FROM '{user_part}'@'{host_part}'")
                        cur.execute("FLUSH PRIVILEGES")
                    db.commit()
                    flash(f"Executed: {priv_action} {privilege} ON {target} for '{user_part}'@'{host_part}'.", "success")
                except Exception as e:
                    flash(f"Error modifying privileges: {e}", "error")

        elif action == "test_query":
            test_user = request.form.get("test_user", "").strip()
            test_password = request.form.get("test_password", "")
            test_sql = request.form.get("test_sql", "").strip()
            test_params = {"user": test_user, "password": test_password, "sql": test_sql}

            try:
                cfg = read_database_config().get("mysql", {})
                socket_path = cfg.get("unix_socket") or "/tmp/mysql.sock"
                conn_user = pymysql.connect(
                    unix_socket=socket_path,
                    user=test_user,
                    password=test_password,
                    database=cfg.get("database", "hospital"),
                    charset="utf8mb4",
                    autocommit=True,
                )
                with conn_user.cursor() as cur:
                    cur.execute(test_sql)
                    if cur.description:
                        columns = [d[0] for d in cur.description]
                        rows = cur.fetchall()
                        formatted_rows = []
                        for r in rows:
                            if isinstance(r, dict):
                                formatted_rows.append([r[c] for c in columns])
                            else:
                                formatted_rows.append(r)
                        test_result = {
                            "success": True,
                            "query": test_sql,
                            "columns": columns,
                            "rows": formatted_rows,
                            "message": f"Query succeeded! Returned {len(rows)} row(s).",
                        }
                    else:
                        test_result = {
                            "success": True,
                            "query": test_sql,
                            "message": f"Query executed successfully! {cur.rowcount} row(s) affected.",
                        }
                conn_user.close()
            except Exception as e:
                test_result = {
                    "success": False,
                    "query": test_sql,
                    "error": str(e),
                }

    users_list = []
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT user, host FROM mysql.user
                WHERE user NOT IN ('mysql.infoschema', 'mysql.session', 'mysql.sys')
                ORDER BY (user = 'root') DESC, user, host
            """)
            raw_users = cur.fetchall()
            for u in raw_users:
                uname = u["user"] if isinstance(u, dict) else u[0]
                uhost = u["host"] if isinstance(u, dict) else u[1]
                grants = []
                try:
                    cur.execute(f"SHOW GRANTS FOR '{uname}'@'{uhost}'")
                    raw_grants = cur.fetchall()
                    for g_row in raw_grants:
                        grant_text = g_row[list(g_row.keys())[0]] if isinstance(g_row, dict) else g_row[0]
                        grants.append(grant_text)
                except Exception:
                    grants.append("Unable to read grants")
                users_list.append({"user": uname, "host": uhost, "grants": grants})
    except Exception as e:
        flash(f"Error loading users: {e}", "error")

    return render_template(
        "access_control.html",
        is_mysql=True,
        users=users_list,
        test_result=test_result,
        test_params=test_params,
    )


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


try:
    ensure_database()
except Exception as _e:
    print(f"Warning: Failed initial ensure_database: {_e}")


if __name__ == "__main__":
    app.run(debug=True)