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
    INSERT INTO PatientAudit (PatientID, Action, Name, PhoneNo)
    VALUES (OLD.ID, 'DELETE', OLD.Name, OLD.PhoneNo);
END//

CREATE TRIGGER DoctorDeleteAudit
AFTER DELETE ON Doctor
FOR EACH ROW
BEGIN
    INSERT INTO DoctorAudit (DoctorID, Action, Name, Email, PhoneNo)
    VALUES (OLD.ID, 'DELETE', OLD.Name, OLD.Email, OLD.PhoneNo);
END//

CREATE TRIGGER BillingInsertAudit
AFTER INSERT ON Billing
FOR EACH ROW
BEGIN
    INSERT INTO BillingAudit (
        TransactionID, Action, NewAmount, NewConsultationID, NewDoctorID
    ) VALUES (
        NEW.TransactionID, 'INSERT', NEW.Amount, NEW.ConsultationID, NEW.DoctorID
    );
END//

CREATE TRIGGER BillingUpdateAudit
AFTER UPDATE ON Billing
FOR EACH ROW
BEGIN
    INSERT INTO BillingAudit (
        TransactionID, Action, OldAmount, NewAmount,
        OldConsultationID, NewConsultationID, OldDoctorID, NewDoctorID
    ) VALUES (
        NEW.TransactionID, 'UPDATE', OLD.Amount, NEW.Amount,
        OLD.ConsultationID, NEW.ConsultationID, OLD.DoctorID, NEW.DoctorID
    );
END//

CREATE TRIGGER BillingDeleteAudit
AFTER DELETE ON Billing
FOR EACH ROW
BEGIN
    INSERT INTO BillingAudit (
        TransactionID, Action, OldAmount, OldConsultationID, OldDoctorID
    ) VALUES (
        OLD.TransactionID, 'DELETE', OLD.Amount, OLD.ConsultationID, OLD.DoctorID
    );
END//

CREATE TRIGGER MedicineTrigger
AFTER INSERT ON Consultation
FOR EACH ROW
BEGIN
    INSERT INTO MedicineGiven (PatientID, Diagnosis, Medicine, DateTime)
    VALUES (NEW.PatientID, NEW.Diagnosis, NEW.Medicine, NEW.DateTime);
END//

DELIMITER ;
