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

The app uses `hospital.db` in the project directory. If the database does not exist, it creates the schema from `init.sql`, `views.sql`, and `triggers.sql`. Existing data is preserved. SQLite foreign-key enforcement is enabled for every application connection.

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Flask routes, SQLite connection, form handling, and database setup |
| `templates/` | Shared layout, dashboard, tables, and entry forms |
| `static/style.css` | Responsive CareDesk interface styles |
| `init.sql` | Core tables and constraints |
| `views.sql` | Age and medicine summary views |
| `triggers.sql` | Medicine history and billing rules |
| `data.py` | Optional Faker-based sample data generator |

## Database notes

Billing follows the existing `PaymentTrigger` rule, so an amount must be greater than zero and below 10,000. New consultations automatically create a medicine-history row through `MedicineTrigger`. The app migrates the older `MedicineGiven` table shape on startup so a patient can have multiple consultation history entries.

For development, run the app with:

```bash
FLASK_DEBUG=1 flask --app app run
```
