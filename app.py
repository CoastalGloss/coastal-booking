import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash

# ---------------- CONFIG ----------------
APP_TITLE = "Coastal Gloss Booking"

# Use /tmp on Render, local file when testing locally
if os.name == "nt":
    DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")
else:
    DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "bookings.db")

app = Flask(__name__)
app.secret_key = "coastal-gloss-secret-key"

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
                service_type TEXT,
                location_type TEXT,
                date TEXT,
                slot TEXT,
                notes TEXT,
                status TEXT
            )
        """)


# Ensure DB always exists (important for Render)
@app.before_request
def ensure_db():
    init_db()


# ---------------- ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        with get_db() as db:
            db.execute("""
                INSERT INTO bookings 
                (created_at, name, phone, vehicle, service_type, location_type, date, slot, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                request.form["name"],
                request.form["phone"],
                request.form["vehicle"],
                request.form["service_type"],
                request.form["location_type"],
                request.form["date"],
                request.form["slot"],
                request.form.get("notes", ""),
                "New"
            ))
        flash("Booking submitted successfully!")
        return redirect("/")

    return render_template_string("""
    <h1>Coastal Gloss Booking</h1>
    <form method="post">
        <input name="name" placeholder="Name" required><br><br>
        <input name="phone" placeholder="Phone" required><br><br>
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
        html += f"<li><b>{b['name']}</b> — {b['date']} {b['slot']} ({b['service_type']})</li>"
    html += "</ul>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
