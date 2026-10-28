import argparse
import json
from pathlib import Path
import random
import re
import sys
from faker import Faker

try:
    import pymysql
except ImportError:
    pymysql = None

import sqlite3

fake = Faker()
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "database_config.json"


def read_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {"db_type": "mysql", "database_name": "hospital.db"}


diagnoses = [
    "Essential (Primary) Hypertension",
    "Type 2 Diabetes Mellitus with Ketoacidosis",
    "Acute Coronary Syndrome",
    "Chronic Obstructive Pulmonary Disease (COPD)",
    "Acute Appendicitis",
    "Major Depressive Disorder",
    "Generalized Anxiety Disorder",
    "Community-Acquired Pneumonia",
    "Gastroesophageal Reflux Disease (GERD)",
    "Osteoarthritis of the Knee",
    "Acute Migraine without Aura",
    "Chronic Kidney Disease, Stage 3",
    "Urinary Tract Infection",
    "Atrial Fibrillation",
    "Iron Deficiency Anemia",
    "Acute Cholecystitis",
    "Hypothyroidism",
    "Lumbar Disc Herniation",
    "Asthma Exacerbation",
    "Benign Prostatic Hyperplasia (BPH)",
    "Ischemic Stroke",
    "Heart Failure with Preserved Ejection Fraction",
    "Rheumatoid Arthritis",
    "Ulcerative Colitis",
]

medicines = [
    "Amoxicillin 500mg",
    "Lisinopril 10mg",
    "Metformin 850mg",
    "Atorvastatin 20mg",
    "Omeprazole 20mg",
    "Albuterol Inhaler",
    "Levothyroxine 50mcg",
    "Amlodipine 5mg",
    "Sertraline 50mg",
    "Ibuprofen 400mg",
    "Gabapentin 300mg",
    "Metoprolol 50mg",
    "Warfarin 5mg",
    "Hydrochlorothiazide 25mg",
]

departments = [
    "Cardiology",
    "Neurology",
    "Pediatrics",
    "Orthopedics",
    "Dermatology",
    "Oncology",
    "Radiology",
    "Gynecology",
    "Urology",
    "Psychiatry",
    "Gastroenterology",
    "General Surgery",
    "Emergency Medicine",
    "Nephrology",
    "Pulmonology",
]

used_phones = set()


def get_unique_phone():
    while True:
        phone = f"{random.randint(2000000000, 9999999999)}"
        if phone not in used_phones:
            used_phones.add(phone)
            return phone


def get_mysql_connection(cfg):
    if pymysql is None:
        raise RuntimeError("PyMySQL is not installed. Please install it using: pip install pymysql")
    mcfg = cfg.get("mysql", {})
    socket_path = mcfg.get("unix_socket")
    if not socket_path:
        for candidate in ["/tmp/mysql.sock", "/var/run/mysqld/mysqld.sock"]:
            if Path(candidate).exists():
                socket_path = candidate
                break

    conn_args = {
        "user": mcfg.get("user", "root"),
        "password": mcfg.get("password", ""),
        "charset": "utf8mb4",
        "autocommit": False,
    }
    if socket_path and Path(socket_path).exists():
        conn_args["unix_socket"] = socket_path
    else:
        conn_args["host"] = mcfg.get("host", "127.0.0.1")
        conn_args["port"] = int(mcfg.get("port", 3306))

    db_name = mcfg.get("database", "hospital")
    # Connect without db first to ensure db exists
    temp_conn = pymysql.connect(**conn_args)
    with temp_conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    temp_conn.close()

    conn_args["database"] = db_name
    conn = pymysql.connect(**conn_args)
    with conn.cursor() as cur:
        cur.execute("SET SESSION sql_mode = 'ANSI_QUOTES,STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION'")
    return conn


def ensure_log_storage(cursor):
    cursor.execute("CREATE DATABASE IF NOT EXISTS hospital_logs")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hospital_logs.LogEntries (
            LogID BIGINT AUTO_INCREMENT PRIMARY KEY,
            LogType VARCHAR(32) NOT NULL,
            Action VARCHAR(10), EntityID INT, TransactionID INT,
            PatientID INT, DoctorID INT, ConsultationID INT,
            Name VARCHAR(120), Email VARCHAR(254), PhoneNo VARCHAR(20),
            Diagnosis TEXT, Medicine TEXT,
            OldAmount DECIMAL(10, 2), NewAmount DECIMAL(10, 2),
            ChangedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_log_type_id (LogType, LogID)
        ) ENGINE=InnoDB
    """)
    cursor.execute("DROP PROCEDURE IF EXISTS hospital_logs.SaveHospitalLog")
    cursor.execute("""
        CREATE PROCEDURE hospital_logs.SaveHospitalLog(
            IN p_log_type VARCHAR(32), IN p_action VARCHAR(10),
            IN p_entity_id INT, IN p_transaction_id INT,
            IN p_patient_id INT, IN p_doctor_id INT,
            IN p_consultation_id INT, IN p_name VARCHAR(120),
            IN p_email VARCHAR(254), IN p_phone_no VARCHAR(20),
            IN p_diagnosis TEXT, IN p_medicine TEXT,
            IN p_old_amount DECIMAL(10, 2), IN p_new_amount DECIMAL(10, 2),
            IN p_changed_at DATETIME
        )
        BEGIN
            INSERT INTO hospital_logs.LogEntries (
                LogType, Action, EntityID, TransactionID, PatientID, DoctorID,
                ConsultationID, Name, Email, PhoneNo, Diagnosis, Medicine,
                OldAmount, NewAmount, ChangedAt
            ) VALUES (
                p_log_type, p_action, p_entity_id, p_transaction_id,
                p_patient_id, p_doctor_id, p_consultation_id, p_name,
                p_email, p_phone_no, p_diagnosis, p_medicine,
                p_old_amount, p_new_amount,
                COALESCE(p_changed_at, CURRENT_TIMESTAMP)
            );
        END
    """)


def populate(db_type="mysql", count_doctors=250, count_patients=500, count_consultations=1000, count_billing=1000):
    cfg = read_config()
    is_mysql = (db_type == "mysql")

    if is_mysql:
        print("Connecting to MySQL...")
        conn = get_mysql_connection(cfg)
        cursor = conn.cursor()

        # Initialize schema if needed
        print("Ensuring MySQL schema, views, and triggers...")
        with open("init_mysql.sql", "r") as f:
            for stmt in f.read().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cursor.execute(stmt)
        with open("views_mysql.sql", "r") as f:
            for stmt in f.read().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cursor.execute(stmt)
        ensure_log_storage(cursor)

        # Triggers
        triggers = [
            ("BillingInsertAudit", """
            CREATE TRIGGER BillingInsertAudit AFTER INSERT ON Billing FOR EACH ROW
            BEGIN
                CALL hospital_logs.SaveHospitalLog(
                    'BILLING', 'INSERT', NEW.TransactionID, NEW.TransactionID, NULL,
                    NEW.DoctorID, NEW.ConsultationID, NULL, NULL, NULL, NULL, NULL,
                    NULL, NEW.Amount, NEW.DateTime
                );
            END
            """),
            ("BillingUpdateAudit", """
            CREATE TRIGGER BillingUpdateAudit AFTER UPDATE ON Billing FOR EACH ROW
            BEGIN
                CALL hospital_logs.SaveHospitalLog(
                    'BILLING', 'UPDATE', NEW.TransactionID, NEW.TransactionID, NULL,
                    NEW.DoctorID, NEW.ConsultATIONID, NULL, NULL, NULL, NULL, NULL,
                    OLD.Amount, NEW.Amount, NEW.DateTime
                );
            END
            """),
            ("BillingDeleteAudit", """
            CREATE TRIGGER BillingDeleteAudit AFTER DELETE ON Billing FOR EACH ROW
            BEGIN
                CALL hospital_logs.SaveHospitalLog(
                    'BILLING', 'DELETE', OLD.TransactionID, OLD.TransactionID, NULL,
                    OLD.DoctorID, OLD.ConsultationID, NULL, NULL, NULL, NULL, NULL,
                    OLD.Amount, NULL, OLD.DateTime
                );
            END
            """),
            ("MedicineTrigger", """
            CREATE TRIGGER MedicineTrigger AFTER INSERT ON Consultation FOR EACH ROW
            BEGIN
                CALL hospital_logs.SaveHospitalLog(
                    'MEDICINE', 'INSERT', NEW.ID, NULL, NEW.PatientID, NEW.DoctorID,
                    NEW.ID, NULL, NULL, NULL, NEW.Diagnosis, NEW.Medicine, NULL, NULL,
                    NEW.DateTime
                );
            END
            """),
        ]
        for name, sql in triggers:
            cursor.execute(f"DROP TRIGGER IF EXISTS `{name}`")
            cursor.execute(sql)
        conn.commit()
    else:
        db_filename = cfg.get("database_name", "hospital.db")
        print(f"Connecting to SQLite ({db_filename})...")
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.executescript(Path("init.sql").read_text())
        cursor.executescript(Path("views.sql").read_text())
        cursor.executescript(Path("triggers.sql").read_text())

    def execute_query(sql, params=()):
        if is_mysql:
            cursor.execute(sql.replace("?", "%s"), params)
        else:
            cursor.execute(sql, params)

    print("Executing DML Inserts...")

    # 1. Departments
    for dept in departments:
        try:
            execute_query('INSERT INTO "Department" ("Name") VALUES (?)', (dept,))
            conn.commit()
        except Exception:
            conn.rollback()

    execute_query('SELECT "ID" FROM "Department"')
    dept_ids = [row[0] for row in cursor.fetchall()]

    # 2. Doctors
    print(f"Inserting {count_doctors} Doctors...")
    for i in range(count_doctors):
        name = f"Dr. {fake.name()}"
        doc_type = random.choice(["Consultant", "Surgeon", "Resident", "Specialist"])
        email = f"doc_{i}_{random.randint(10000, 99999)}@{fake.free_email_domain()}"
        phone = get_unique_phone()
        birthdate = fake.date_of_birth(minimum_age=30, maximum_age=65).strftime("%Y-%m-%d")
        dept_id = random.choice(dept_ids)
        salary = random.randint(50000, 250000)

        execute_query(
            '''INSERT INTO "Doctor" ("Name", "Type", "Email", "PhoneNo", "birthdate", "Department", "Salary")
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (name, doc_type, email, phone, birthdate, dept_id, salary),
        )

    # 3. Patients
    print(f"Inserting {count_patients} Patients...")
    for _ in range(count_patients):
        name = fake.name()
        city = fake.city()
        phone = get_unique_phone()
        street = fake.street_address()
        pincode = random.randint(10000, 99999)
        birthdate = fake.date_of_birth(minimum_age=0, maximum_age=90).strftime("%Y-%m-%d")

        execute_query(
            '''INSERT INTO "Patient" ("Name", "City", "PhoneNo", "Street", "Pincode", "birthdate")
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, city, phone, street, pincode, birthdate),
        )

    conn.commit()

    execute_query('SELECT "ID" FROM "Doctor"')
    doc_ids = [row[0] for row in cursor.fetchall()]

    execute_query('SELECT "ID" FROM "Patient"')
    patient_ids = [row[0] for row in cursor.fetchall()]

    # 4. Consultations
    print(f"Inserting {count_consultations} Consultations...")
    for _ in range(count_consultations):
        pid = random.choice(patient_ids)
        did = random.choice(doc_ids)
        diag = random.choice(diagnoses)
        med = random.choice(medicines)
        test_type = random.randint(1, 5)

        execute_query(
            '''INSERT INTO "Consultation" ("PatientID", "DoctorID", "Diagnosis", "Medicine", "TestType")
               VALUES (?, ?, ?, ?, ?)''',
            (pid, did, diag, med, test_type),
        )

    conn.commit()

    execute_query('SELECT "ID" FROM "Consultation"')
    consultation_ids = [row[0] for row in cursor.fetchall()]

    # 5. Billing
    print(f"Inserting {count_billing} Billing transactions...")
    for _ in range(count_billing):
        cid = random.choice(consultation_ids)
        did = random.choice(doc_ids)
        amount = random.randint(1500, 9500)

        execute_query(
            '''INSERT INTO "Billing" ("ConsultationID", "DoctorID", "Amount")
               VALUES (?, ?, ?)''',
            (cid, did, amount),
        )

    conn.commit()
    conn.close()
    print(f"Successfully populated {db_type.upper()} with {count_patients} Patients, {count_doctors} Doctors, and {count_consultations} Consultations!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate sample data for CareDesk Hospital Management")
    parser.add_argument("--mysql", action="store_true", help="Populate MySQL database")
    parser.add_argument("--sqlite", action="store_true", help="Populate SQLite database")
    args = parser.parse_args()

    cfg = read_config()
    target = "mysql" if args.mysql else ("sqlite" if args.sqlite else cfg.get("db_type", "mysql"))
    populate(db_type=target)