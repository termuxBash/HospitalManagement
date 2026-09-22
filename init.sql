CREATE TABLE "Billing" (
    "TransactionID" INTEGER PRIMARY KEY AUTOINCREMENT,
    "ConsultationID" INTEGER,
    "DoctorID"      INTEGER,
    "Amount"        NUMERIC NOT NULL DEFAULT 10000 CHECK("Amount" > 0),
    "DateTime"      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("ConsultationID") REFERENCES "Consultation"("ID") ON DELETE SET NULL,
    FOREIGN KEY ("DoctorID") REFERENCES "Doctor"("ID") ON DELETE SET NULL
);
CREATE TABLE "Consultation" (
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
CREATE TABLE "Department" (
    "ID"    INTEGER PRIMARY KEY AUTOINCREMENT,
    "Name"  TEXT NOT NULL UNIQUE
);
CREATE TABLE "Doctor" (
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
CREATE TABLE "Patient" (
    "ID"         INTEGER PRIMARY KEY AUTOINCREMENT,
    "Name"       TEXT NOT NULL,
    "City"       TEXT NOT NULL,
    "PhoneNo"    TEXT NOT NULL UNIQUE,
    "Street"     TEXT,
    "Pincode"    INTEGER NOT NULL,
    "birthdate"  TEXT
);