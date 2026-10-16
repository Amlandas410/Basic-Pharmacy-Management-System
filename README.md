# Basic Pharmacy Management System

A browser-based pharmacy inventory, billing, and sales application built with
Python Flask and MySQL. The system provides a dashboard for day-to-day
operations, medicine stock management, direct sales, and multi-item customer
bills.

> **Project status:** This is a small educational/demo application. It does not
> include user accounts, role-based permissions, audit controls, or production
> deployment hardening. Do not use it to manage real pharmacy operations or
> sensitive customer data without a thorough review and the safeguards required
> for your location.

## Features

- Dashboard summaries for medicine count, total stock, sales, revenue,
  inventory cost/value, recorded profit, low stock, and expired inventory.
- Medicine catalog management: add, update, search, and delete medicine
  records.
- Medicine details include category, manufacturer, batch number, expiry date,
  purchase/selling prices, quantity, and reorder level.
- Stock status and search by medicine name, category, or batch number.
- Validation prevents saving a medicine with an expiry date that is today or
  earlier, or a selling price below its purchase price.
- Record a single-medicine sale or create a bill containing multiple medicines.
- Stock is reduced when a sale is recorded; bills are handled in a database
  transaction and reject requests when stock is insufficient.
- Customer name and bill number are stored with each bill and its sales lines.
- Print the current bill or download it as a JSON e-bill.
- Review recent sales with quantities, revenue, profit, and date.

## Technology

- **Frontend:** HTML, CSS, and JavaScript
- **Backend:** Python 3, Flask
- **Database:** MySQL Server 8.x
- **MySQL driver:** `mysql-connector-python`
- **Environment configuration:** `.env` via `python-dotenv`

## Requirements

- Python 3.9 or newer
- MySQL Server 8.x running locally or reachable from the application
- A MySQL user allowed to create/use the database and tables

XAMPP, Apache, and phpMyAdmin are not required. You may use MySQL Workbench or
another MySQL client to set up the database.

## Project structure

```text
.
├── app.py                  # Flask application and JSON API
├── database/
│   └── pharmacy.sql        # Database schema and demo medicine records
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Main application page
├── static/
│   ├── css/                # Application styles
│   └── js/                 # Browser-side application logic
├── .env.example            # Safe template for local DB settings
└── README.md
```

## Setup on Windows

### 1. Start MySQL Server

Make sure the MySQL service is running. The default connection settings expect
MySQL at `127.0.0.1:3306`.

### 2. Create the database and demo data

Run `database/pharmacy.sql` using MySQL Workbench, the MySQL command-line
client, or another MySQL client.

> **Warning:** The SQL script drops and recreates the `medicines`, `sales`, and
> `bills` tables. Running it again deletes the data in those tables. Use it
> only for a fresh/demo database, not a database containing data you need.

The script creates the `pharmacy_db` database and three tables, then inserts a
few sample medicines. On application startup, the app also checks/creates the
bill table and adds the bill-related columns to an older `sales` table if they
are missing.

### 3. Configure the database connection

In PowerShell, copy the example file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set the host, port, MySQL user, and password for your
installation:

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=replace-with-your-local-password
MYSQL_DATABASE=pharmacy_db
```

If the selected MySQL account has no password, leave `MYSQL_PASSWORD` empty.
The `.env` file is for local use and is excluded from Git; do not commit
credentials or replace `.env.example` with real secrets.

### 4. Create a virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents activating the virtual environment, either use
Command Prompt with `.venv\Scripts\activate.bat` or configure the appropriate
PowerShell execution policy for your machine.

### 5. Run the application

```powershell
python app.py
```

Open <http://127.0.0.1:5000> in a browser. The included Flask server is for
local development; use a production WSGI server and secure deployment
configuration before exposing an instance to a network.

## Using the application

1. **Dashboard:** Review inventory, sales, revenue, profit, low-stock, and
   expired-item totals.
2. **Medicines:** Add or edit medicine details, search inventory, or delete a
   medicine that has no sales history.
3. **Billing:** Add one or more medicine/quantity lines, enter an optional
   customer name, then generate the bill. Successful billing records the sale
   and reduces stock. Print or download the generated bill as needed.
4. **Sales:** Record a direct sale or view recent sale lines.

## HTTP API

The Flask application serves the web interface at `/` and exposes these JSON
endpoints:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/dashboard` | Dashboard totals and inventory alerts |
| `GET` | `/api/medicines` | List medicines; accepts optional `search` query |
| `POST` | `/api/medicines` | Add a medicine |
| `PUT` | `/api/medicines/<medicine_id>` | Update a medicine |
| `DELETE` | `/api/medicines/<medicine_id>` | Delete a medicine without sales history |
| `POST` | `/api/sales` | Record a single-medicine sale |
| `GET` | `/api/sales` | List sales |
| `POST` | `/api/bills` | Create a bill and record its medicine sales |
| `GET` | `/api/bills/<bill_no>` | Retrieve a bill and its items |

Write endpoints that accept data expect JSON request bodies. Validation and
database errors are returned as JSON error messages with an appropriate HTTP
status.

## Database tables

- **`medicines`** stores catalog details, expiry, prices, quantity, and reorder
  level.
- **`sales`** stores one row per sold medicine line, including the unit cost,
  unit price, revenue, profit, customer, and optional bill number.
- **`bills`** stores bill number, customer, total, and creation time.

## Troubleshooting

- **Cannot connect to MySQL:** Confirm the service is running, the host/port
  are correct, and the firewall allows the connection.
- **Access denied:** Check `MYSQL_USER` and `MYSQL_PASSWORD` in `.env`.
- **Unknown database:** Run `database/pharmacy.sql` against MySQL.
- **Missing Python package:** Activate the virtual environment and run
  `pip install -r requirements.txt`.
- **Port 5000 is already in use:** Stop the process using that port or change
  the development port in `app.py`.
