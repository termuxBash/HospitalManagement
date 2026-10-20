-- =======================================================
-- DCL (Data Control Language) Operations in MySQL
-- Demonstrates: CREATE USER, SELECT, GRANT, FLUSH PRIVILEGES,
--               switching users, testing permissions, REVOKE,
--               and verifying permission denied error.
-- =======================================================

-- 1. Create a hospital staff user named 'employee'.
-- Replace 'employee_password' with the password you want to use.
CREATE USER IF NOT EXISTS 'employee'@'localhost' IDENTIFIED BY 'employee_password';

-- 2. View all MySQL users and verify that employee exists.
SELECT user, host FROM mysql.user WHERE user = 'employee';

-- 3. Give employee read and insert access to patient records.
-- Clear any previous grants so the exercise starts from a known state.
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'employee'@'localhost';
GRANT SELECT, INSERT ON hospital.Patient TO 'employee'@'localhost';

-- 4. Flush privileges to apply changes immediately
FLUSH PRIVILEGES;

-- 5. The INSERT privilege is included above. Check the effective grants.
SHOW GRANTS FOR 'employee'@'localhost';
FLUSH PRIVILEGES;

-- =======================================================
-- Testing as user 'employee':
-- Open a terminal and run:
--   mysql -u employee -p -D hospital
-- Enter the password chosen above.
-- USE hospital;
-- INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
-- VALUES ('Employee Test Patient', 'Care City', '9000000012', 'Staff Road', 400001, '1990-01-01');
-- SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000012';
-- =======================================================

-- 6. Revoke INSERT while retaining read-only access.
REVOKE INSERT ON hospital.Patient FROM 'employee'@'localhost';
GRANT SELECT ON hospital.Patient TO 'employee'@'localhost';
FLUSH PRIVILEGES;

-- Alternative direct revoke if only INSERT was granted:
-- REVOKE INSERT ON hospital.Patient FROM 'employee'@'localhost';
-- FLUSH PRIVILEGES;

-- =======================================================
-- Testing verification after REVOKE:
-- In the employee user's terminal, try inserting again:
--   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
--   VALUES ('Denied Patient', 'Care City', '9000000013', 'Staff Road', 400001, '1990-01-01');
--
-- Expected Output / Error Message:
--   ERROR 1142 (42000): INSERT command denied to user 'employee'@'localhost' for table 'Patient'
-- =======================================================
