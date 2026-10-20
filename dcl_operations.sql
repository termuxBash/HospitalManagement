-- DCL OPERATIONS

CREATE USER IF NOT EXISTS 'employee'@'localhost' IDENTIFIED BY 'employee_password';
SELECT user, host FROM mysql.user WHERE user = 'employee';
GRANT INSERT ON hospital.Patient TO 'employee'@'localhost';
FLUSH PRIVILEGES;

-- Login as employee and run the following command.
-- mysql -u employee -p -D hospital
-- INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
-- VALUES ('Employee Test Patient', 'Care City', '9000000012', 'Staff Road', 400001, '1990-01-01');

REVOKE INSERT ON hospital.Patient FROM 'employee'@'localhost';
FLUSH PRIVILEGES;

-- INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
-- VALUES ('Denied Patient', 'Care City', '9000000013', 'Staff Road', 400001, '1990-01-01');
