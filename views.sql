CREATE VIEW "DoctorWithAge" AS
SELECT *, 
    (strftime('%Y', 'now') - strftime('%Y', "birthdate")) - 
    (strftime('%m-%d', 'now') < strftime('%m-%d', "birthdate")) AS "age"
FROM "Doctor";

CREATE VIEW "PatientWithAge" AS
SELECT *, 
    (strftime('%Y', 'now') - strftime('%Y', "birthdate")) - 
    (strftime('%m-%d', 'now') < strftime('%m-%d', "birthdate")) AS "age"
FROM "Patient";

CREATE VIEW "MedicineCount" AS
SELECT "Medicine", COUNT(*) AS "PrescriptionCount"
FROM "Consultation"
WHERE "Medicine" IS NOT NULL AND TRIM("Medicine") <> ''
GROUP BY "Medicine";

CREATE VIEW "ConsultationDetails" AS
SELECT c."ID" AS "ConsultationID", c."DateTime", c."Diagnosis", c."Medicine", c."TestType",
       p."ID" AS "PatientID", p."Name" AS "PatientName", p."PhoneNo" AS "PatientPhone",
       d."ID" AS "DoctorID", d."Name" AS "DoctorName", d."Type" AS "DoctorType",
       dept."Name" AS "DepartmentName"
FROM "Consultation" c
JOIN "Patient" p ON p."ID" = c."PatientID"
JOIN "Doctor" d ON d."ID" = c."DoctorID"
LEFT JOIN "Department" dept ON dept."ID" = d."Department";

CREATE VIEW "DoctorWorkload" AS
SELECT d."ID" AS "DoctorID", d."Name" AS "DoctorName", dept."Name" AS "DepartmentName",
       COUNT(c."ID") AS "ConsultationCount", MAX(c."DateTime") AS "LastConsultation"
FROM "Doctor" d
LEFT JOIN "Department" dept ON dept."ID" = d."Department"
LEFT JOIN "Consultation" c ON c."DoctorID" = d."ID"
GROUP BY d."ID", d."Name", dept."Name";

CREATE VIEW "PatientCareSummary" AS
SELECT p."ID" AS "PatientID", p."Name" AS "PatientName", p."PhoneNo",
       COUNT(c."ID") AS "ConsultationCount", MAX(c."DateTime") AS "LastVisit",
       COUNT(DISTINCT c."DoctorID") AS "DoctorsSeen"
FROM "Patient" p
LEFT JOIN "Consultation" c ON c."PatientID" = p."ID"
GROUP BY p."ID", p."Name", p."PhoneNo";

CREATE VIEW "BillingSummary" AS
SELECT b."TransactionID", b."DateTime", b."Amount", b."ConsultationID",
       p."Name" AS "PatientName", d."Name" AS "DoctorName", c."Diagnosis"
FROM "Billing" b
LEFT JOIN "Consultation" c ON c."ID" = b."ConsultationID"
LEFT JOIN "Patient" p ON p."ID" = c."PatientID"
LEFT JOIN "Doctor" d ON d."ID" = b."DoctorID";