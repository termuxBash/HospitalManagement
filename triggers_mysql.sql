-- CareDesk Hospital Management - MySQL Triggers
-- Audits billing operations and tracks prescribed medicines

DROP TRIGGER IF EXISTS BillingInsertAudit;
DROP TRIGGER IF EXISTS BillingUpdateAudit;
DROP TRIGGER IF EXISTS BillingDeleteAudit;
DROP TRIGGER IF EXISTS MedicineTrigger;
DROP TRIGGER IF EXISTS PatientDeleteAudit;
DROP TRIGGER IF EXISTS DoctorDeleteAudit;

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
