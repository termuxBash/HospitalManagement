CREATE TRIGGER PaymentTrigger
BEFORE INSERT ON Billing
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.amount >= 10000 THEN
            RAISE(ABORT, 'Payment cannot be processed. Max amount is 10000.')
    END;
END;

CREATE TRIGGER MedicineTrigger
AFTER INSERT ON Consultation
FOR EACH ROW
BEGIN
    INSERT INTO MedicineGiven VALUES (NEW.PatientID, NEW.Diagnosis, NEW.Medicine, NEW.DateTime);
END;
