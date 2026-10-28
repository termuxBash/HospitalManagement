# CareDesk - Hospital Management System

CareDesk is a Flask clinical operations web application backed by **MySQL** (with InnoDB transaction support) and local **SQLite**. It features clinical dashboards, patient/doctor directories, consultation logs, billing ledgers with audit history, automated triggers, analytical views, and dedicated scripts for **TCL** and **DCL** database operations.

---

## Features

- **Dual Database Engine**: Native support for **MySQL** (primary) and **SQLite** with instant switching from the UI or `database_config.json`.
- **Web-Based DCL & Access Control**: Create MySQL users, grant and revoke privileges on hospital tables, view effective grants, and test queries as any user directly from the browser UI.
- **DCL & TCL Lab Operations**: Complete support for Data Control Language (`CREATE USER`, `GRANT`, `REVOKE`) and Transaction Control Language (`START TRANSACTION`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`).
- **Clinical Dashboard**: Overview of patients, active doctors, consultations, and billing volume.
- **Patient & Doctor Directories**: Searchable records with calculated ages via database views.
- **Consultation & Medicine Tracking**: Prescriptions automatically logged to medicine history using triggers.
- **Billing Ledger & Audit Trail**: Real-time audit log of all billing insertions, updates, and removals.
- **Centralized MySQL Logs**: Billing, medicine, patient, and doctor audit events are written through the `SaveHospitalLog` stored procedure to the separate `hospital_logs` database.
- **Table-Level Constraints**: Salary and billing constraints enforced directly at the database engine level.

---

## Quick Start

### 1. Requirements

- Python 3.10+
- MySQL Server (or MariaDB)
- Python packages: `Flask`, `PyMySQL`, `cryptography`, `Faker`

```bash
python3 -m pip install Flask PyMySQL cryptography Faker
```

### 2. Configure Database

CareDesk defaults to **MySQL** in `database_config.json`:

```json
{
  "db_type": "mysql",
  "database_name": "hospital.db",
  "mysql": {
    "host": "localhost",
   "port": 3306,
    "user": "root",
   "password": "mint",
    "database": "hospital",
   "unix_socket": "/var/run/mysqld/mysqld.sock"
  }
}
```

*Note: You can easily switch between MySQL and SQLite anytime from the **Database** menu in the sidebar.*

### 3. Initialize & Populate Sample Data

To populate the MySQL database with 500 patients, 250 doctors, 1,000 consultations, and 1,000 billing records:

```bash
# Populate MySQL:
python3 data.py --mysql

# Or populate SQLite:
python3 data.py --sqlite
```

### 4. Run the Web Application

```bash
python3 app.py
```

Open `http://127.0.0.1:5000` in your web browser.

**Staff Login Credentials:**
- **Username**: `hospital`
- **Password**: `hospital123`

---

## TCL & DCL Operations in MySQL

CareDesk includes dedicated SQL scripts ready to run in the MySQL terminal.

### DCL Operations (Data Control Language)

Run or review `dcl_operations.sql`:

```bash
mysql -u root -p hospital < dcl_operations.sql
```

#### Step-by-Step Interactive Guide:

1. **Create the employee user:**
   ```sql
   CREATE USER 'employee'@'localhost' IDENTIFIED BY 'employee_password';
   ```

2. **Verify user creation:**
   ```sql
   SELECT user, host FROM mysql.user WHERE user='employee';
   ```

3. **Grant privileges:**
   ```sql
   GRANT SELECT, INSERT ON hospital.Patient TO 'employee'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. **Log in as the new user and insert data:**
   ```bash
   mysql -u employee -p -D hospital
   # Enter the employee password
   ```
   ```sql
   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
   VALUES ('Employee Test Patient', 'Care City', '9000000012', 'Staff Road', 400001, '1990-01-01');
   SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000012';
   exit;
   ```

5. **Revoke the privilege (as root):**
   ```sql
   REVOKE INSERT ON hospital.Patient FROM 'employee'@'localhost';
   GRANT SELECT ON hospital.Patient TO 'employee'@'localhost';
   FLUSH PRIVILEGES;
   ```

6. **Verify privilege revocation (error output):**
   Log back in as `employee` and attempt to insert:
   ```sql
   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
   VALUES ('Denied Patient', 'Care City', '9000000013', 'Staff Road', 400001, '1990-01-01');
   ```
   **Expected Error Output:**
   ```text
   ERROR 1142 (42000): INSERT command denied to user 'employee'@'localhost' for table 'Patient'
   ```

---

### TCL Operations (Transaction Control Language)

Run or review `tcl_operations.sql`:

```bash
mysql -u root -p hospital < tcl_operations.sql
```

The same commands are available from the authenticated **TCL Lab** page in
the web application. Each submitted script runs on one database connection
with a `session_start` savepoint created before the script. Use
`ROLLBACK TO SAVEPOINT session_start` to return to the state at the beginning
of the Flask database session, and `COMMIT` to retain changes and initialize a
new session savepoint. The TCL Lab also provides buttons for both actions.
Statements are separated by semicolons; logging out rolls back uncommitted
MySQL changes.

#### Step-by-Step Interactive Guide:

1. **Initial Patient State:**
   ```sql
   USE hospital;
   SELECT ID, Name, City, PhoneNo FROM Patient ORDER BY ID;
   ```

2. **Transaction 1: `START TRANSACTION` & `COMMIT`:**
   ```sql
   START TRANSACTION;
   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
   VALUES ('TCL Committed Patient', 'Care City', '9000000020', 'Main Road', 400001, '1990-01-01');
   COMMIT;

   -- The patient is now permanently committed
   SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000020';
   ```

3. **Transaction 2: Testing `ROLLBACK` after `COMMIT`:**
   ```sql
   ROLLBACK;
   -- The committed patient remains because COMMIT was already executed
   SELECT ID, Name, PhoneNo FROM Patient WHERE PhoneNo = '9000000020';
   ```

4. **Transaction 3: `SAVEPOINT` and `ROLLBACK TO SAVEPOINT`:**
   ```sql
   START TRANSACTION;
   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
   VALUES ('TCL Savepoint Patient', 'Care City', '9000000021', 'Main Road', 400001, '1991-01-01');
   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
   VALUES ('TCL Second Patient', 'Care City', '9000000022', 'Main Road', 400001, '1992-01-01');

   -- Set savepoint sp1:
   SAVEPOINT sp1;

   -- Insert another patient after savepoint:
   INSERT INTO Patient (Name, City, PhoneNo, Street, Pincode, birthdate)
   VALUES ('TCL Rolled Back Patient', 'Care City', '9000000023', 'Main Road', 400001, '1993-01-01');
   SELECT ID, Name, PhoneNo FROM Patient
   WHERE PhoneNo IN ('9000000021', '9000000022', '9000000023');

   -- Roll back to savepoint sp1:
   ROLLBACK TO SAVEPOINT sp1;

   -- Commit the remaining transaction:
   COMMIT;

   -- Final check: the third patient was discarded, while the first two remain.
   SELECT ID, Name, PhoneNo FROM Patient
   WHERE PhoneNo IN ('9000000021', '9000000022', '9000000023');
   ```

---

### Centralized MySQL log storage

The MySQL audit triggers call `hospital_logs.SaveHospitalLog`. The procedure
writes every event to `hospital_logs.LogEntries`, keeping application logs
separate from the clinical data in `hospital`. The setup is applied
automatically by the application and can also be installed manually:

```bash
mysql -u root -p < stored_procedure_mysql.sql
```

The complete database, procedure, migration, and trigger SQL is in
`stored_procedure_mysql.sql`.

## Project Structure

| File | Purpose |
| --- | --- |
| `app.py` | Flask application with dual MySQL / SQLite connection abstraction, forms, and routes |
| `database_config.json` | Configuration file storing active engine (`mysql` or `sqlite`) and connection credentials |
| `init_mysql.sql` | MySQL DDL schema (InnoDB tables, constraints, and foreign keys) |
| `views_mysql.sql` | MySQL analytical views using `TIMESTAMPDIFF` for age and clinical summaries |
| `triggers_mysql.sql` | MySQL triggers for billing audits (`BillingAudit`) and consultation medicines (`MedicineGiven`) |
| `dcl_operations.sql` | Executable DCL script (`CREATE USER`, `GRANT`, `REVOKE`, permission verification) |
| `tcl_operations.sql` | Executable TCL script (`START TRANSACTION`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`) |
| `init.sql` | SQLite schema and table definitions |
| `views.sql` | SQLite view definitions |
| `triggers.sql` | SQLite audit and medicine trigger definitions |
| `data.py` | Sample data generator supporting both `--mysql` and `--sqlite` |
| `templates/` | Jinja2 templates (dashboard, directories, billing, forms, database settings) |
| `static/style.css` | CareDesk responsive UI styling |
