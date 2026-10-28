-- CareDesk Hospital Management - centralized MySQL log storage
-- Run this script while connected as a user allowed to create databases,
-- procedures, and triggers.

CREATE DATABASE IF NOT EXISTS hospital_logs;

CREATE TABLE IF NOT EXISTS hospital_logs.LogEntries (
    LogID BIGINT AUTO_INCREMENT PRIMARY KEY,
    LogType VARCHAR(32) NOT NULL,
    Action VARCHAR(10),
    EntityID INT,
    TransactionID INT,
    PatientID INT,
    DoctorID INT,
    ConsultationID INT,
    Name VARCHAR(120),
    Email VARCHAR(254),
    PhoneNo VARCHAR(20),
    Diagnosis TEXT,
    Medicine TEXT,
    OldAmount DECIMAL(10, 2),
    NewAmount DECIMAL(10, 2),
    ChangedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_log_type_id (LogType, LogID),
    INDEX idx_log_patient (PatientID),
    INDEX idx_log_doctor (DoctorID)
) ENGINE=InnoDB;

INSERT INTO hospital_logs.LogEntries
    (LogType, Action, EntityID, TransactionID, ConsultationID, DoctorID,
     OldAmount, NewAmount, ChangedAt)
SELECT 'BILLING', Action, TransactionID, TransactionID,
       COALESCE(NewConsultationID, OldConsultationID),
       COALESCE(NewDoctorID, OldDoctorID), OldAmount, NewAmount, ChangedAt
FROM hospital.BillingAudit
WHERE NOT EXISTS (
    SELECT 1 FROM hospital_logs.LogEntries WHERE LogType = 'BILLING'
);

INSERT INTO hospital_logs.LogEntries
    (LogType, Action, EntityID, PatientID, Name, PhoneNo, ChangedAt)
SELECT 'PATIENT', Action, PatientID, PatientID, Name, PhoneNo, ChangedAt
FROM hospital.PatientAudit
WHERE NOT EXISTS (
    SELECT 1 FROM hospital_logs.LogEntries WHERE LogType = 'PATIENT'
);

INSERT INTO hospital_logs.LogEntries
    (LogType, Action, EntityID, DoctorID, Name, Email, PhoneNo, ChangedAt)
SELECT 'DOCTOR', Action, DoctorID, DoctorID, Name, Email, PhoneNo, ChangedAt
FROM hospital.DoctorAudit
WHERE NOT EXISTS (
    SELECT 1 FROM hospital_logs.LogEntries WHERE LogType = 'DOCTOR'
);

INSERT INTO hospital_logs.LogEntries
    (LogType, Action, EntityID, PatientID, Diagnosis, Medicine, ChangedAt)
SELECT 'MEDICINE', 'INSERT', ID, PatientID, Diagnosis, Medicine, DateTime
FROM hospital.MedicineGiven
WHERE NOT EXISTS (
    SELECT 1 FROM hospital_logs.LogEntries WHERE LogType = 'MEDICINE'
);

DROP PROCEDURE IF EXISTS hospital_logs.SaveHospitalLog;

DELIMITER //
CREATE PROCEDURE hospital_logs.SaveHospitalLog(
    IN p_log_type VARCHAR(32),
    IN p_action VARCHAR(10),
    IN p_entity_id INT,
    IN p_transaction_id INT,
    IN p_patient_id INT,
    IN p_doctor_id INT,
    IN p_consultation_id INT,
    IN p_name VARCHAR(120),
    IN p_email VARCHAR(254),
    IN p_phone_no VARCHAR(20),
    IN p_diagnosis TEXT,
    IN p_medicine TEXT,
    IN p_old_amount DECIMAL(10, 2),
    IN p_new_amount DECIMAL(10, 2),
    IN p_changed_at DATETIME
)
BEGIN
    INSERT INTO hospital_logs.LogEntries (
        LogType, Action, EntityID, TransactionID, PatientID, DoctorID,
        ConsultationID, Name, Email, PhoneNo, Diagnosis, Medicine,
        OldAmount, NewAmount, ChangedAt
    ) VALUES (
        p_log_type, p_action, p_entity_id, p_transaction_id, p_patient_id,
        p_doctor_id, p_consultation_id, p_name, p_email, p_phone_no,
        p_diagnosis, p_medicine, p_old_amount, p_new_amount,
        COALESCE(p_changed_at, CURRENT_TIMESTAMP)
    );
END//
DELIMITER ;

-- Existing audit tables are retained for backward compatibility. New events
-- are written to hospital_logs.LogEntries by the triggers below.
USE hospital;

DROP TRIGGER IF EXISTS PatientDeleteAudit;
DROP TRIGGER IF EXISTS DoctorDeleteAudit;
DROP TRIGGER IF EXISTS BillingInsertAudit;
DROP TRIGGER IF EXISTS BillingUpdateAudit;
DROP TRIGGER IF EXISTS BillingDeleteAudit;
DROP TRIGGER IF EXISTS MedicineTrigger;

DELIMITER //
CREATE TRIGGER PatientDeleteAudit
AFTER DELETE ON Patient
FOR EACH ROW
BEGIN
    CALL hospital_logs.SaveHospitalLog(
        'PATIENT', 'DELETE', OLD.ID, NULL, OLD.ID, NULL, NULL,
        OLD.Name, NULL, OLD.PhoneNo, NULL, NULL, NULL, NULL, NULL
    );
END//

CREATE TRIGGER DoctorDeleteAudit
AFTER DELETE ON Doctor
FOR EACH ROW
BEGIN
    CALL hospital_logs.SaveHospitalLog(
        'DOCTOR', 'DELETE', OLD.ID, NULL, NULL, OLD.ID, NULL,
        OLD.Name, OLD.Email, OLD.PhoneNo, NULL, NULL, NULL, NULL, NULL
    );
END//

CREATE TRIGGER BillingInsertAudit
AFTER INSERT ON Billing
FOR EACH ROW
BEGIN
    CALL hospital_logs.SaveHospitalLog(
        'BILLING', 'INSERT', NEW.TransactionID, NEW.TransactionID, NULL,
        NEW.DoctorID, NEW.ConsultationID, NULL, NULL, NULL, NULL, NULL,
        NULL, NEW.Amount, NEW.DateTime
    );
END//

CREATE TRIGGER BillingUpdateAudit
AFTER UPDATE ON Billing
FOR EACH ROW
BEGIN
    CALL hospital_logs.SaveHospitalLog(
        'BILLING', 'UPDATE', NEW.TransactionID, NEW.TransactionID, NULL,
        NEW.DoctorID, NEW.ConsultationID, NULL, NULL, NULL, NULL, NULL,
        OLD.Amount, NEW.Amount, NEW.DateTime
    );
END//

CREATE TRIGGER BillingDeleteAudit
AFTER DELETE ON Billing
FOR EACH ROW
BEGIN
    CALL hospital_logs.SaveHospitalLog(
        'BILLING', 'DELETE', OLD.TransactionID, OLD.TransactionID, NULL,
        OLD.DoctorID, OLD.ConsultationID, NULL, NULL, NULL, NULL, NULL,
        OLD.Amount, NULL, OLD.DateTime
    );
END//

CREATE TRIGGER MedicineTrigger
AFTER INSERT ON Consultation
FOR EACH ROW
BEGIN
    CALL hospital_logs.SaveHospitalLog(
        'MEDICINE', 'INSERT', NEW.ID, NULL, NEW.PatientID, NEW.DoctorID,
        NEW.ID, NULL, NULL, NULL, NEW.Diagnosis, NEW.Medicine, NULL, NULL,
        NEW.DateTime
    );
END//
DELIMITER ;
