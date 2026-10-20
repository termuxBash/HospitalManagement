-- TCL OPERATIONS

USE hospital;

START TRANSACTION;
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Committed Patient', 'Care City', '9000000020', 'Main Road', 400001, '1990-01-01');
COMMIT;
SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000020';

ROLLBACK;
SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000020';

START TRANSACTION;
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Savepoint Patient', 'Care City', '9000000021', 'Main Road', 400001, '1991-01-01');
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Second Patient', 'Care City', '9000000022', 'Main Road', 400001, '1992-01-01');
SAVEPOINT sp1;
SELECT ID, Name, PhoneNo FROM Patient
WHERE PhoneNo IN ('9000000021', '9000000022');
INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
VALUES ('TCL Rolled Back Patient', 'Care City', '9000000023', 'Main Road', 400001, '1993-01-01');
SELECT ID, Name, PhoneNo FROM Patient
WHERE PhoneNo IN ('9000000021', '9000000022', '9000000023');

ROLLBACK TO SAVEPOINT sp1;
COMMIT;
SELECT ID, Name, PhoneNo FROM Patient
WHERE PhoneNo IN ('9000000021', '9000000022', '9000000023');
