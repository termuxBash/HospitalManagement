# Hospital Management

CareDesk is a small Flask application for entering and reviewing hospital data backed by SQLite. It uses the existing DML structure in `init.sql`, with database views and triggers from `views.sql` and `triggers.sql`.

## Features

- Dashboard with patient, doctor, consultation, and billing totals
- Patient directory with search by name, city, or phone
- Doctor and department directory
- Consultation entry linked to an existing patient and doctor
- Billing ledger linked to consultations
- Friendly validation messages for duplicate records, invalid relationships, and billing limits
- Responsive interface for desktop and mobile screens

## Run locally

Python 3.10+ and Flask are required.

```bash
python3 -m pip install Flask
python3 app.py
```

Open `http://127.0.0.1:5000` in a browser.

The application requires a simple staff login before any records or database settings can be opened:

- Username: `hosptial`
- Password: `hospital123`

The app uses the filename in `database_config.json` (default: `hospital.db`). Use **Database** in the sidebar to change it. A new database is created from `init.sql`, `views.sql`, and `triggers.sql`; the selected filename is persisted for the next startup. Existing data is preserved. SQLite foreign-key enforcement is enabled for every application connection.

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Flask routes, SQLite connection, form handling, and database setup |
| `templates/` | Shared layout, dashboard, tables, and entry forms |
| `static/style.css` | Responsive CareDesk interface styles |
| `init.sql` | Core tables and constraints |
| `views.sql` | Age, consultation, workload, patient-care, billing, and medicine summary views |
| `triggers.sql` | Medicine history plus billing insert/update/delete audit triggers |
| `database_config.json` | Persisted SQLite database filename selected in the app |
| `data.py` | Optional Faker-based sample data generator |

## Database notes

Billing uses a table-level check constraint, so an amount must be greater than zero and below 10,000. Billing changes are stored in `BillingAudit` and can be reviewed from the Billing page. New consultations automatically create a medicine-history row through `MedicineTrigger`. The app migrates the older `MedicineGiven` table shape on startup so a patient can have multiple consultation history entries.

For development, run the app with:

```bash
FLASK_DEBUG=1 flask --app app run
```
