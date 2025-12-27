import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash

# -----------------------
# CONFIG
# -----------------------
APP_TITLE = "Coastal Gloss Booking"

# Database path (works on Render + local)
if os.name == "nt":
    DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")
else:
    DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "bookings.db")

# -----------------------
# APP SETUP
# -----------------------
app = Flask(__name__)
app.secret_key = "super-secret-key-change-me"


# -----------------------
# DATABASE SETUP
# -----------------------
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
                service_type TEXT,
                location_type TEXT,
                date TEXT,
                slot TEXT,
                notes TEXT,
                status TEXT
            )
        """)


# Run DB setup on startup
init_db()


# -----------------------
# ROUTES
# -----------------------

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        vehicle = request.form["vehicle"]
        service = request.form["service_type"]
        location = request.form["location_type"]
        date = request.form["date"]
        slot = request.form["slot"]
        notes = request.form.get("notes", "")

        with get_db() as db:
            db.execute("""
                INSERT INTO bookings 
                (created_at, name, phone, vehicle, service_type, location_type, date, slot, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                name, phone, vehicle, service, location, date, slot, notes, "New"
            ))

        flash("Booking submitted successfully!")
        return redirect("/")

    return render_template_string("""
    <h2>Coastal Gloss Booking</h2>
    <form method="post">
        <input name="name" placeholder="Full Name" required><br><br>
        <input name="phone" placeholder="Phone Number" required><br><br>
        <input name="vehicle" placeholder="Vehicle" required><br><br>

        <label>Service</label><br>
        <select name="service_type">
            <option>Mobile Detail</option>
            <option>Ceramic Coating</option>
        </select><br><br>

        <label>Location</label><br>
        <select name="location_type">
            <option>Mobile</option>
            <option>Drop Off</option>
        </select><br><br>

        <label>Date</label><br>
        <input type="date" name="date" required><br><br>

        <label>Time</label><br>
        <select name="slot">
            <option>9:00 AM</option>
            <option>12:00 PM</option>
            <option>3:00 PM</option>
        </select><br><br>

        <textarea name="notes" placeholder="Notes"></textarea><br><br>

        <button type="submit">Book Now</button>
    </form>
    """)
    

@app.route("/admin")
def admin():
    with get_db() as db:
        bookings = db.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()

    html = "<h1>Admin Panel</h1><ul>"
    for b in bookings:
        html += f"<li><b>{b['name']}</b> – {b['date']} {b['slot']} – {b['service_type']}</li>"
    html += "</ul>"
    return html


# -----------------------
# RUN APP
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
