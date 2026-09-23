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

CREATE VIEW MedicineCount AS
SELECT Medicine, COUNT(*)
FROM Consultation GROUP BY Medicine;