from datetime import date, datetime
from decimal import Decimal
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
import mysql.connector
import os
from mysql.connector import Error

load_dotenv()

app = Flask(__name__)

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "pharmacy_db"),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def ensure_billing_schema():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bill_no VARCHAR(20) UNIQUE,
                customer_name VARCHAR(120) NOT NULL DEFAULT 'Walk-in customer',
                grand_total DECIMAL(10,2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for statement in (
            "ALTER TABLE sales ADD COLUMN customer_name VARCHAR(120) NOT NULL DEFAULT 'Walk-in customer'",
            "ALTER TABLE sales ADD COLUMN bill_no VARCHAR(20) NULL",
        ):
            try:
                cur.execute(statement)
            except Error as exc:
                if exc.errno != 1060:
                    raise
        conn.commit()
    finally:
        cur.close()
        conn.close()


def row_to_dict(cursor, row):
    result = {}
    for key, value in zip(cursor.column_names, row):
        if isinstance(value, (date,)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = float(value)
        result[key] = value
    return result


def bill_payload(bill_no, customer_name, items, total):
    return {
        "bill_no": bill_no,
        "customer_name": customer_name,
        "bill_date": datetime.now().isoformat(timespec="seconds"),
        "items": items,
        "grand_total": float(total),
    }


def validate_expiry(expiry_value):
    try:
        expiry = date.fromisoformat(str(expiry_value))
    except (TypeError, ValueError):
        return "Expiry date must be a valid date."
    if expiry <= date.today():
        return "Expiry date must be after today."
    return None


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/dashboard")
def dashboard():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*), COALESCE(SUM(quantity),0) FROM medicines")
        medicine_count, stock_count = cur.fetchone()

        cur.execute("SELECT COUNT(*), COALESCE(SUM(total_amount),0) FROM sales")
        sales_count, sales_total = cur.fetchone()

        cur.execute("""
            SELECT COALESCE(SUM(purchase_price * quantity),0),
                   COALESCE(SUM(selling_price * quantity),0)
            FROM medicines
        """)
        inventory_cost, inventory_value = cur.fetchone()

        cur.execute("SELECT COALESCE(SUM(profit_amount),0) FROM sales")
        profit_total = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM medicines WHERE quantity <= reorder_level")
        low_stock = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM medicines WHERE expiry_date < CURDATE()")
        expired = cur.fetchone()[0]

        return jsonify({
            "medicine_count": medicine_count,
            "stock_count": stock_count,
            "sales_count": sales_count,
            "sales_total": float(sales_total),
            "inventory_cost": float(inventory_cost),
            "inventory_value": float(inventory_value),
            "profit_total": float(profit_total),
            "low_stock": low_stock,
            "expired": expired,
        })
    finally:
        cur.close()
        conn.close()


@app.get("/api/medicines")
def list_medicines():
    search = request.args.get("search", "").strip()
    conn = get_db()
    cur = conn.cursor()
    try:
        sql = """
            SELECT id, medicine_name, category, manufacturer, batch_no,
                     expiry_date, purchase_price, selling_price, quantity, reorder_level,
                     quantity * selling_price AS stock_value
            FROM medicines
        """
        params = []
        if search:
            sql += " WHERE medicine_name LIKE %s OR category LIKE %s OR batch_no LIKE %s"
            term = f"%{search}%"
            params.extend([term, term, term])
        sql += " ORDER BY id DESC"
        cur.execute(sql, params)
        return jsonify([row_to_dict(cur, row) for row in cur.fetchall()])
    finally:
        cur.close()
        conn.close()


@app.post("/api/medicines")
def add_medicine():
    data = request.get_json() or {}
    required = ["medicine_name", "category", "expiry_date", "purchase_price", "selling_price", "quantity", "reorder_level"]
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    expiry_error = validate_expiry(data["expiry_date"])
    if expiry_error:
        return jsonify({"error": expiry_error}), 400
    if float(data["selling_price"]) < float(data["purchase_price"]):
        return jsonify({"error": "Selling price cannot be lower than buying price."}), 400

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO medicines
            (medicine_name, category, manufacturer, batch_no, expiry_date,
             purchase_price, selling_price, quantity, reorder_level)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["medicine_name"], data["category"], data.get("manufacturer", ""),
            data.get("batch_no", ""), data["expiry_date"], data["purchase_price"],
            data["selling_price"],
            data["quantity"], data["reorder_level"]
        ))
        conn.commit()
        return jsonify({"message": "Medicine added", "id": cur.lastrowid}), 201
    except Error as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    finally:
        cur.close()
        conn.close()


@app.put("/api/medicines/<int:medicine_id>")
def update_medicine(medicine_id):
    data = request.get_json() or {}
    expiry_error = validate_expiry(data.get("expiry_date"))
    if expiry_error:
        return jsonify({"error": expiry_error}), 400
    if float(data.get("selling_price", 0)) < float(data.get("purchase_price", 0)):
        return jsonify({"error": "Selling price cannot be lower than buying price."}), 400
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE medicines SET medicine_name=%s, category=%s, manufacturer=%s,
            batch_no=%s, expiry_date=%s, purchase_price=%s, selling_price=%s,
            quantity=%s, reorder_level=%s
            WHERE id=%s
        """, (
            data.get("medicine_name"), data.get("category"), data.get("manufacturer", ""),
            data.get("batch_no", ""), data.get("expiry_date"), data.get("purchase_price"),
            data.get("selling_price"),
            data.get("quantity"), data.get("reorder_level"), medicine_id
        ))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Medicine not found"}), 404
        return jsonify({"message": "Medicine updated"})
    except Error as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    finally:
        cur.close()
        conn.close()


@app.delete("/api/medicines/<int:medicine_id>")
def delete_medicine(medicine_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM medicines WHERE id=%s", (medicine_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Medicine not found"}), 404
        return jsonify({"message": "Medicine deleted"})
    except Error as exc:
        conn.rollback()
        return jsonify({"error": "Cannot delete medicine with sales history."}), 400
    finally:
        cur.close()
        conn.close()


@app.post("/api/sales")
def create_sale():
    data = request.get_json() or {}
    medicine_id = data.get("medicine_id")
    quantity = int(data.get("quantity", 0))
    if not medicine_id or quantity <= 0:
        return jsonify({"error": "Valid medicine_id and quantity are required"}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cur.execute("SELECT * FROM medicines WHERE id=%s FOR UPDATE", (medicine_id,))
        med = cur.fetchone()
        if not med:
            conn.rollback()
            return jsonify({"error": "Medicine not found"}), 404
        if med["quantity"] < quantity:
            conn.rollback()
            return jsonify({"error": "Insufficient stock"}), 400
        total = Decimal(str(med["selling_price"])) * quantity
        profit = (Decimal(str(med["selling_price"])) - Decimal(str(med["purchase_price"]))) * quantity
        cur.execute("UPDATE medicines SET quantity=quantity-%s WHERE id=%s", (quantity, medicine_id))
        cur.execute("""
            INSERT INTO sales
                (medicine_id, medicine_name, quantity, unit_price, unit_cost,
                 total_amount, profit_amount, customer_name, bill_no)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (medicine_id, med["medicine_name"], quantity, med["selling_price"],
              med["purchase_price"], total, profit, "Walk-in customer", None))
        conn.commit()
        return jsonify({"message": "Sale recorded", "total": float(total), "profit": float(profit)})
    except Error as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    finally:
        cur.close()
        conn.close()


@app.post("/api/bills")
def create_bill():
    data = request.get_json() or {}
    customer_name = str(data.get("customer_name", "Walk-in customer")).strip() or "Walk-in customer"
    requested_items = data.get("items") or []
    if not requested_items:
        return jsonify({"error": "Add at least one medicine to the bill."}), 400

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        cur.execute("INSERT INTO bills (customer_name, grand_total) VALUES (%s, 0)", (customer_name,))
        bill_id = cur.lastrowid
        bill_no = f"{1000 + bill_id:04d}"
        items = []
        grand_total = Decimal("0")

        for requested in requested_items:
            medicine_id = requested.get("medicine_id")
            quantity = int(requested.get("quantity", 0))
            if not medicine_id or quantity <= 0:
                raise ValueError("Every bill item needs a valid medicine and quantity.")
            cur.execute("SELECT * FROM medicines WHERE id=%s FOR UPDATE", (medicine_id,))
            med = cur.fetchone()
            if not med:
                raise ValueError("One of the selected medicines no longer exists.")
            if med["quantity"] < quantity:
                raise ValueError(f"Insufficient stock for {med['medicine_name']}.")
            total = Decimal(str(med["selling_price"])) * quantity
            profit = (Decimal(str(med["selling_price"])) - Decimal(str(med["purchase_price"]))) * quantity
            cur.execute("UPDATE medicines SET quantity=quantity-%s WHERE id=%s", (quantity, medicine_id))
            cur.execute("""
                INSERT INTO sales
                    (medicine_id, medicine_name, quantity, unit_price, unit_cost,
                     total_amount, profit_amount, customer_name, bill_no)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (medicine_id, med["medicine_name"], quantity, med["selling_price"],
                  med["purchase_price"], total, profit, customer_name, bill_no))
            items.append({
                "medicine_name": med["medicine_name"],
                "quantity": quantity,
                "unit_price": float(med["selling_price"]),
                "total_amount": float(total),
            })
            grand_total += total

        cur.execute("UPDATE bills SET bill_no=%s, grand_total=%s WHERE id=%s", (bill_no, grand_total, bill_id))
        conn.commit()
        return jsonify(bill_payload(bill_no, customer_name, items, grand_total)), 201
    except (Error, ValueError, TypeError) as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    finally:
        cur.close()
        conn.close()


@app.get("/api/bills/<bill_no>")
def get_bill(bill_no):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT bill_no, customer_name, grand_total, created_at FROM bills WHERE bill_no=%s", (bill_no,))
        bill = cur.fetchone()
        if not bill:
            return jsonify({"error": "Bill not found"}), 404
        cur.execute("""
            SELECT medicine_name, quantity, unit_price, total_amount
            FROM sales WHERE bill_no=%s ORDER BY id
        """, (bill_no,))
        bill["items"] = cur.fetchall()
        bill["grand_total"] = float(bill["grand_total"])
        bill["items"] = [{
            **item,
            "unit_price": float(item["unit_price"]),
            "total_amount": float(item["total_amount"]),
        } for item in bill["items"]]
        return jsonify(bill)
    finally:
        cur.close()
        conn.close()


@app.get("/api/sales")
def list_sales():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, medicine_name, quantity, unit_price, total_amount, profit_amount,
                   customer_name, bill_no, sold_at
            FROM sales ORDER BY id DESC
        """)
        return jsonify([row_to_dict(cur, row) for row in cur.fetchall()])
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    ensure_billing_schema()
    app.run(debug=True)
