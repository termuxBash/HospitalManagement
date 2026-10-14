-- CareDesk Hospital Management - MySQL Schema
-- Uses InnoDB engine to support Foreign Keys and Transactions (TCL)

CREATE TABLE IF NOT EXISTS Department (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Doctor (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(120) NOT NULL,
    Type VARCHAR(50),
    Email VARCHAR(255) NOT NULL UNIQUE,
    PhoneNo VARCHAR(20) NOT NULL UNIQUE,
    birthdate DATE,
    Department INT,
    Salary INT NOT NULL DEFAULT 10000 CHECK (Salary > 1000),
    FOREIGN KEY (Department) REFERENCES Department(ID) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Patient (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    Name VARCHAR(120) NOT NULL,
    City VARCHAR(100) NOT NULL,
    PhoneNo VARCHAR(20) NOT NULL UNIQUE,
    Street VARCHAR(200),
    Pincode INT NOT NULL,
    birthdate DATE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Consultation (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    PatientID INT NOT NULL,
    DoctorID INT NOT NULL,
    Diagnosis TEXT,
    Medicine TEXT,
    TestType INT,
    DateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (PatientID) REFERENCES Patient(ID) ON DELETE CASCADE,
    FOREIGN KEY (DoctorID) REFERENCES Doctor(ID) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS Billing (
    TransactionID INT AUTO_INCREMENT PRIMARY KEY,
    ConsultationID INT,
    DoctorID INT,
    Amount DECIMAL(10, 2) NOT NULL DEFAULT 5000 CHECK (Amount > 0 AND Amount < 10000),
    DateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ConsultationID) REFERENCES Consultation(ID) ON DELETE SET NULL,
    FOREIGN KEY (DoctorID) REFERENCES Doctor(ID) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS MedicineGiven (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    PatientID INT NOT NULL,
    Diagnosis TEXT,
    Medicine TEXT,
    DateTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS BillingAudit (
    AuditID INT AUTO_INCREMENT PRIMARY KEY,
    TransactionID INT,
    Action VARCHAR(10) NOT NULL CHECK (Action IN ('INSERT', 'UPDATE', 'DELETE')),
    OldAmount DECIMAL(10, 2),
    NewAmount DECIMAL(10, 2),
    OldConsultationID INT,
    NewConsultationID INT,
    OldDoctorID INT,
    NewDoctorID INT,
    ChangedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Product table used for TCL and DCL operations
CREATE TABLE IF NOT EXISTS product (
    product_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price INT,
    qty INT,
    description VARCHAR(255)
) ENGINE=InnoDB;

-- Initial data for product table (from hint)
INSERT INTO product (product_id, name, price, qty, description) VALUES
(1, 'Ferrero', 500, 5, 'chocolate'),
(2, 'Kurkure', 50, 1, 'snacks'),
(3, 'lays', 120, 1, 'snacks'),
(4, 'thepla', 92, 8, 'snacks'),
(5, 'pickle', 300, 3, 'snacks'),
(6, 'dorritos', 2020, 2, 'snacks'),
(7, 'LogitechG650', 500, 2, 'Mouse')
ON DUPLICATE KEY UPDATE name=VALUES(name);
