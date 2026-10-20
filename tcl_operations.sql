-- =======================================================
-- TCL (Transaction Control Language) Operations in MySQL
-- Demonstrates: START TRANSACTION, COMMIT, ROLLBACK,
--               SAVEPOINT, and ROLLBACK TO SAVEPOINT.
-- Note: MySQL InnoDB engine is required for transactions.
-- =======================================================

USE hospital;

-- Reset only the test patients from this lab so the script is repeatable.
DELETE FROM Patient
WHERE PhoneNo IN ('9000000020', '9000000021', '9000000022', '9000000023');

-- Verify the hospital table used by this transaction exercise.
SELECT ID, Name, City, PhoneNo FROM Patient ORDER BY ID;

-- -------------------------------------------------------
-- Part 1: START TRANSACTION and COMMIT
-- -------------------------------------------------------
START TRANSACTION;

-- Insert a patient and permanently save the record.
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Committed Patient', 'Care City', '9000000020', 'Main Road', 400001, '1990-01-01');

-- Permanently save changes to the database
COMMIT;

-- The committed patient remains in the table.
SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000020';

-- -------------------------------------------------------
-- Part 2: Testing ROLLBACK on committed data
-- -------------------------------------------------------
-- Because COMMIT was executed earlier, ROLLBACK here has no effect on the patient
ROLLBACK;

-- Verify the committed patient is still present.
SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000020';

-- -------------------------------------------------------
-- Part 3: SAVEPOINT and ROLLBACK TO SAVEPOINT
-- -------------------------------------------------------
START TRANSACTION;

-- Add two patients before the savepoint.
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Savepoint Patient', 'Care City', '9000000021', 'Main Road', 400001, '1991-01-01');
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Second Patient', 'Care City', '9000000022', 'Main Road', 400001, '1992-01-01');

-- Create a savepoint marker 'sp1'
SAVEPOINT sp1;

SELECT ID, Name, PhoneNo FROM Patient
WHERE PhoneNo IN ('9000000021', '9000000022');

-- Insert another patient after the savepoint.
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Rolled Back Patient', 'Care City', '9000000023', 'Main Road', 400001, '1993-01-01');

-- This temporary patient is visible until the rollback below.
SELECT ID, Name, PhoneNo FROM Patient
WHERE PhoneNo IN ('9000000021', '9000000022', '9000000023');

-- Rollback uncommitted changes back to savepoint 'sp1'
-- This removes only the patient inserted after sp1.
ROLLBACK TO SAVEPOINT sp1;

-- Commit the remaining transaction
COMMIT;

-- Verify final results:
-- The first two savepoint patients remain; the rolled-back patient is absent.
SELECT ID, Name, PhoneNo FROM Patient
WHERE PhoneNo IN ('9000000021', '9000000022', '9000000023');
