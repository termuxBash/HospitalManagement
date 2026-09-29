CREATE TRIGGER "BillingInsertAudit"
AFTER INSERT ON "Billing"
FOR EACH ROW
BEGIN
    INSERT INTO "BillingAudit" (
        "TransactionID", "Action", "NewAmount", "NewConsultationID", "NewDoctorID"
    ) VALUES (
        NEW."TransactionID", 'INSERT', NEW."Amount", NEW."ConsultationID", NEW."DoctorID"
    );
END;

CREATE TRIGGER "BillingUpdateAudit"
AFTER UPDATE ON "Billing"
FOR EACH ROW
BEGIN
    INSERT INTO "BillingAudit" (
        "TransactionID", "Action", "OldAmount", "NewAmount",
        "OldConsultationID", "NewConsultationID", "OldDoctorID", "NewDoctorID"
    ) VALUES (
        NEW."TransactionID", 'UPDATE', OLD."Amount", NEW."Amount",
        OLD."ConsultationID", NEW."ConsultationID", OLD."DoctorID", NEW."DoctorID"
    );
END;

CREATE TRIGGER "BillingDeleteAudit"
AFTER DELETE ON "Billing"
FOR EACH ROW
BEGIN
    INSERT INTO "BillingAudit" (
        "TransactionID", "Action", "OldAmount", "OldConsultationID", "OldDoctorID"
    ) VALUES (
        OLD."TransactionID", 'DELETE', OLD."Amount", OLD."ConsultationID", OLD."DoctorID"
    );
END;

CREATE TRIGGER "MedicineTrigger"
AFTER INSERT ON "Consultation"
FOR EACH ROW
BEGIN
    INSERT INTO "MedicineGiven" ("PatientID", "Diagnosis", "Medicine", "DateTime")
    VALUES (NEW."PatientID", NEW."Diagnosis", NEW."Medicine", NEW."DateTime");
END;
