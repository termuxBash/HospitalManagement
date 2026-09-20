import random
import sqlite3
from faker import Faker

fake = Faker()
db_filename = "hospital.db"

# Connect and enable foreign keys
conn = sqlite3.connect(db_filename)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Read and execute schema from init.sql
print("Initializing database schema from init.sql...")
with open("init.sql", "r") as f:
  schema_sql = f.read()
cursor.executescript(schema_sql)

# --- REALISTIC DATASETS ---
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
    phone = f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    if phone not in used_phones:
      used_phones.add(phone)
      return phone


# --- DML INSERTS ---

print("Executing DML Inserts...")

# 1. Departments
for dept in departments:
  try:
    cursor.execute('INSERT INTO "Department" ("Name") VALUES (?)', (dept,))
  except sqlite3.IntegrityError:
    pass
conn.commit()

cursor.execute('SELECT "ID" FROM "Department"')
dept_ids = [row[0] for row in cursor.fetchall()]

# 2. Doctors (250 records)
print("Inserting 250 Doctors...")
for i in range(250):
  name = f"Dr. {fake.name()}"
  doc_type = random.choice(
      ["Consultant", "Surgeon", "Resident", "Specialist"]
  )
  email = f"doc_{i}_{random.randint(10000, 99999)}@{fake.free_email_domain()}"
  phone = get_unique_phone()
  birthdate = fake.date_of_birth(minimum_age=30, maximum_age=65).strftime(
      "%Y-%m-%d"
  )
  dept_id = random.choice(dept_ids)
  salary = random.randint(50000, 250000)

  cursor.execute(
      """
        INSERT INTO "Doctor" ("Name", "Type", "Email", "PhoneNo", "birthdate", "Department", "Salary")
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
      (name, doc_type, email, phone, birthdate, dept_id, salary),
  )

# 3. Patients (500 records)
print("Inserting 500 Patients...")
for _ in range(500):
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
        INSERT INTO "Patient" ("Name", "City", "PhoneNo", "Street", "Pincode", "birthdate")
        VALUES (?, ?, ?, ?, ?, ?)
    """,
      (name, city, phone, street, pincode, birthdate),
  )

conn.commit()

cursor.execute('SELECT "ID" FROM "Doctor"')
doc_ids = [row[0] for row in cursor.fetchall()]

cursor.execute('SELECT "ID" FROM "Patient"')
patient_ids = [row[0] for row in cursor.fetchall()]

# 4. Consultations (1,000 records)
print("Inserting 1,000 Consultations...")
for _ in range(1000):
  pid = random.choice(patient_ids)
  did = random.choice(doc_ids)
  diag = random.choice(diagnoses)
  med = random.choice(medicines)
  test_type = random.randint(1, 5)

  cursor.execute(
      """
        INSERT INTO "Consultation" ("PatientID", "DoctorID", "Diagnosis", "Medicine", "TestType")
        VALUES (?, ?, ?, ?, ?)
    """,
      (pid, did, diag, med, test_type),
  )

conn.commit()

cursor.execute('SELECT "ID" FROM "Consultation"')
consultation_ids = [row[0] for row in cursor.fetchall()]

# 5. Billing (1,000 records)
print("Inserting 1,000 Billing transactions...")
for _ in range(1000):
  cid = random.choice(consultation_ids)
  did = random.choice(doc_ids)
  amount = random.randint(1500, 45000)

  cursor.execute(
      """
        INSERT INTO "Billing" ("ConsultationID", "DoctorID", "Amount")
        VALUES (?, ?, ?)
    """,
      (cid, did, amount),
  )

conn.commit()
conn.close()

print(
    f"Successfully populated '{db_filename}' with 500 Patients, 250 Doctors,"
    " and 1,000 Records!"
)