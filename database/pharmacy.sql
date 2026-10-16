CREATE DATABASE IF NOT EXISTS pharmacy_db;
USE pharmacy_db;

DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS bills;
DROP TABLE IF EXISTS medicines;

CREATE TABLE medicines (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(120) NOT NULL,
    category VARCHAR(80) NOT NULL,
    manufacturer VARCHAR(120),
    batch_no VARCHAR(50),
    expiry_date DATE NOT NULL,
    purchase_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    selling_price DECIMAL(10,2) NOT NULL DEFAULT 0,
    quantity INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 10,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    medicine_id INT NOT NULL,
    medicine_name VARCHAR(120) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    unit_cost DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    profit_amount DECIMAL(10,2) NOT NULL,
    customer_name VARCHAR(120) NOT NULL DEFAULT 'Walk-in customer',
    bill_no VARCHAR(20),
    sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE RESTRICT
);

CREATE TABLE bills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bill_no VARCHAR(20) UNIQUE,
    customer_name VARCHAR(120) NOT NULL DEFAULT 'Walk-in customer',
    grand_total DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO medicines (medicine_name, category, manufacturer, batch_no, expiry_date, purchase_price, selling_price, quantity, reorder_level) VALUES
('Paracetamol 500mg', 'Tablet', 'ABC Pharma', 'PCM001', '2027-06-30', 2.00, 2.50, 120, 20),
('Amoxicillin 250mg', 'Capsule', 'XYZ Pharma', 'AMX101', '2027-02-15', 4.00, 5.00, 60, 15),
('Cetirizine 10mg', 'Tablet', 'MediCare', 'CTZ202', '2026-12-20', 1.00, 1.50, 12, 20),
('Cough Syrup 100ml', 'Syrup', 'HealthPlus', 'CS333', '2028-01-10', 65.00, 85.00, 30, 5);
