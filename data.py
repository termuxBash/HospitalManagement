import random
import sqlite3
from faker import Faker

# Initialize Faker and SQLite connection
fake = Faker()
conn = sqlite3.connect("hospital.db")
cursor = conn.cursor()

# Enable foreign keys in SQLite
cursor.execute("PRAGMA foreign_keys = ON;")

print("Creating tables...")

# 1. Create Tables (Notice: 'age' is removed from table definitions)
cursor.executescript("""
CREATE TABLE IF NOT EXISTS "Department" (
    "ID"    INTEGER PRIMARY KEY AUTOINCREMENT,
    "Name"  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS "Doctor" (
    "ID"         INTEGER PRIMARY KEY AUTOINCREMENT,
    "Name"       TEXT NOT NULL,
    "Type"       TEXT,
    "Email"      TEXT NOT NULL UNIQUE,
    "PhoneNo"    TEXT NOT NULL UNIQUE,
    "birthdate"  TEXT,
    "Department" INTEGER,
    "Salary"     INTEGER NOT NULL DEFAULT 10000 CHECK("Salary" > 1000),
    FOREIGN KEY ("Department") REFERENCES "Department"("ID")
);

CREATE TABLE IF NOT EXISTS "Patient" (
    "ID"         INTEGER PRIMARY KEY AUTOINCREMENT,
    "Name"       TEXT NOT NULL,
    "City"       TEXT NOT NULL,
    "PhoneNo"    TEXT NOT NULL UNIQUE,
    "Street"     TEXT,
    "Pincode"    INTEGER NOT NULL,
    "birthdate"  TEXT
);

CREATE TABLE IF NOT EXISTS "Consultation" (
    "ID"        INTEGER PRIMARY KEY AUTOINCREMENT,
    "PatientID" INTEGER NOT NULL,
    "DoctorID"  INTEGER NOT NULL,
    "Diagnosis" TEXT,
    "Medicine"  TEXT,
    "TestType"  INTEGER,
    "DateTime"  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("PatientID") REFERENCES "Patient"("ID") ON DELETE CASCADE,
    FOREIGN KEY ("DoctorID") REFERENCES "Doctor"("ID") ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS "Billing" (
    "TransactionID" INTEGER PRIMARY KEY AUTOINCREMENT,
    "ConsultationID" INTEGER,
    "DoctorID"      INTEGER,
    "Amount"        NUMERIC NOT NULL DEFAULT 10000 CHECK("Amount" > 0),
    "DateTime"      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("ConsultationID") REFERENCES "Consultation"("ID") ON DELETE SET NULL,
    FOREIGN KEY ("DoctorID") REFERENCES "Doctor"("ID") ON DELETE SET NULL
);

-- SQLite Views to retrieve Age dynamically on query
CREATE VIEW IF NOT EXISTS "DoctorWithAge" AS
SELECT *, 
    (strftime('%Y', 'now') - strftime('%Y', "birthdate")) - 
    (strftime('%m-%d', 'now') < strftime('%m-%d', "birthdate")) AS "age"
FROM "Doctor";

CREATE VIEW IF NOT EXISTS "PatientWithAge" AS
SELECT *, 
    (strftime('%Y', 'now') - strftime('%Y', "birthdate")) - 
    (strftime('%m-%d', 'now') < strftime('%m-%d', "birthdate")) AS "age"
FROM "Patient";
""")

print("Generating and inserting data...")

# 2. Departments (50 unique medical fields)
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
    "Ophthalmology",
    "ENT",
    "Anesthesiology",
    "Gastroenterology",
    "Nephrology",
    "Pulmonology",
    "Endocrinology",
    "Rheumatology",
    "Hematology",
    "Immunology",
    "General Surgery",
    "Emergency Medicine",
    "Pathology",
    "Geriatrics",
    "Infectious Diseases",
    "Plastic Surgery",
    "Vascular Surgery",
    "Thoracic Surgery",
    "Neurosurgery",
    "Orthopedic Surgery",
    "Sports Medicine",
    "Physical Medicine",
    "Palliative Care",
    "Neonatology",
    "Perinatology",
    "Critical Care",
    "Hepatology",
    "Proctology",
    "Andrology",
    "Internal Medicine",
    "Family Medicine",
    "Occupational Medicine",
    "Public Health",
    "Medical Genetics",
    "Pain Management",
    "Sleep Medicine",
    "Nuclear Medicine",
    "Allergy",
    "Epidemiology",
    "Trauma Surgery",
]

for dept in departments:
  try:
    cursor.execute("INSERT INTO Department (Name) VALUES (?)", (dept,))
  except sqlite3.IntegrityError:
    pass
conn.commit()

# Fetch Department IDs
cursor.execute("SELECT ID FROM Department")
dept_ids = [row[0] for row in cursor.fetchall()]

# Helper to avoid Phone Number duplicate collisions
used_phones = set()


def get_unique_phone():
  while True:
    phone = f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    if phone not in used_phones:
      used_phones.add(phone)
      return phone


# 3. Doctors (50 records)
for i in range(50):
  name = fake.name()
  doc_type = random.choice(
      ["Consultant", "Surgeon", "Resident", "Specialist"]
  )
  email = f"doc_{i}_{random.randint(1000, 9999)}@{fake.free_email_domain()}"
  phone = get_unique_phone()
  birthdate = fake.date_of_birth(minimum_age=30, maximum_age=65).strftime(
      "%Y-%m-%d"
  )
  dept_id = random.choice(dept_ids)
  salary = random.randint(15000, 150000)

  cursor.execute(
      """
        INSERT INTO Doctor (Name, Type, Email, PhoneNo, birthdate, Department, Salary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
      (name, doc_type, email, phone, birthdate, dept_id, salary),
  )
conn.commit()

# Fetch Doctor IDs
cursor.execute("SELECT ID FROM Doctor")
doc_ids = [row[0] for row in cursor.fetchall()]

# 4. Patients (50 records)
for i in range(50):
  name = fake.name()
  city = fake.city()
  phone = get_unique_phone()
  street = fake.street_address()
  pincode = random.randint(10000, 99999)
  birthdate = fake.date_of_birth(minimum_age=0, maximum_age=90).strftime(
      "%Y-%m-%d"
  )

  cursor.execute(
      """
        INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (name, city, phone, street, pincode, birthdate),
  )
conn.commit()

# Fetch Patient IDs
cursor.execute("SELECT ID FROM Patient")
patient_ids = [row[0] for row in cursor.fetchall()]

# 5. Consultations (50 records)
diagnoses = [
    "Hypertension",
    "Type 2 Diabetes",
    "Common Cold",
    "Asthma",
    "Migraine",
    "Gastroenteritis",
    "Bronchitis",
    "Anxiety",
    "Arthritis",
    "Allergic Rhinitis",
]
medicines = [
    "Paracetamol",
    "Ibuprofen",
    "Amoxicillin",
    "Metformin",
    "Lisinopril",
    "Salbutamol",
    "Omeprazole",
    "Cetirizine",
]

for _ in range(50):
  pid = random.choice(patient_ids)
  did = random.choice(doc_ids)
  diag = random.choice(diagnoses)
  med = random.choice(medicines)
  test_type = random.randint(1, 5)

  cursor.execute(
      """
        INSERT INTO Consultation (PatientID, DoctorID, Diagnosis, Medicine, TestType)
        VALUES (?, ?, ?, ?, ?)
    """,
      (pid, did, diag, med, test_type),
  )
conn.commit()

# Fetch Consultation IDs
cursor.execute("SELECT ID FROM Consultation")
consultation_ids = [row[0] for row in cursor.fetchall()]

# 6. Billing (50 records)
for _ in range(50):
  cid = random.choice(consultation_ids)
  did = random.choice(doc_ids)
  amount = random.randint(500, 25000)

  cursor.execute(
      """
        INSERT INTO Billing (ConsultationID, DoctorID, Amount)
        VALUES (?, ?, ?)
    """,
      (cid, did, amount),
  )

conn.commit()
conn.close()

print("Successfully populated hospital database!")