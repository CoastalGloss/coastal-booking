import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, render_template_string

# ---------------- CONFIG ----------------
APP_TITLE = "Coastal Gloss Booking"

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "bookings.db")

app = Flask(__name__)
app.secret_key = "coastal-gloss-secret"

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                name TEXT,
                phone TEXT,
                vehicle TEXT,
                service TEXT,
                location TEXT,
                date TEXT,
                time TEXT,
                notes TEXT
            )
        """)

init_db()

# ---------------- ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def booking():
    if request.method == "POST":
        with get_db() as db:
            db.execute("""
                INSERT INTO bookings
                (created_at, name, phone, vehicle, service, location, date, time, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                request.form["name"],
                request.form["phone"],
                request.form["vehicle"],
                request.form["service"],
                request.form["location"],
                request.form["date"],
                request.form["time"],
                request.form.get("notes", "")
            ))
        return "<h2>Booking Received!</h2><p>You may close this window.</p>"

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Coastal Gloss Booking</title>
<style>
body { font-family: Arial; max-width: 720px; margin: auto; padding: 20px; }
input, select, textarea { width: 100%; padding: 10px; margin-bottom: 12px; }
button { padding: 14px; font-size: 16px; background: black; color: white; border: none; }
h1 { margin-bottom: 5px; }
</style>
</head>

<body>
<h1>Coastal Gloss – Booking Request</h1>

<form method="post">

<label>Full Name</label>
<input name="name" required>

<label>Phone Number</label>
<input name="phone" required>

<label>Vehicle</label>
<input name="vehicle" required>

<label>Service Package</label>
<select name="service">
<option>SUPREME LUXURY EXTERIOR RESET – $105</option>
<option>SUPREME LUXURY EXTERIOR REFRESH – $65</option>
<option>WASH N COAT CERAMIC (1 YEAR) – $499</option>
<option>POLISH N COAT CERAMIC (2 YEAR) – $749</option>
<option>PREMIUM CERAMIC (5 YEAR) – $1499</option>
<option>INTERIOR DETAIL – $165</option>
<option>INTERIOR REFRESH – $85</option>
</select>

<label>Service Location</label>
<select name="location">
<option>Mobile</option>
<option>Drop Off</option>
</select>

<label>Preferred Date</label>
<input type="date" name="date" required>

<label>Time Slot</label>
<select name="time">
<option>9:00 AM</option>
<option>12:00 PM</option>
<option>3:00 PM</option>
</select>

<label>Notes / Add-ons</label>
<textarea name="notes"></textarea>

<button type="submit">Book Appointment</button>
</form>

</body>
</html>
""")

@app.route("/admin")
def admin():
    with get_db() as db:
        rows = db.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()

    html = "<h1>Admin Panel</h1>"
    for r in rows:
        html += f"""
        <div style='border:1px solid #ccc;padding:10px;margin:10px'>
            <strong>{r['name']}</strong> – {r['service']}<br>
            {r['date']} @ {r['time']}<br>
            {r['phone']} | {r['vehicle']}<br>
            {r['location']}<br>
            <em>{r['notes']}</em>
        </div>
        """
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
