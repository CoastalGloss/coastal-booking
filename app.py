import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, render_template_string, flash

app = Flask(__name__)
app.secret_key = "coastal-gloss-secret"

# ---------------- DATABASE ----------------
DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "bookings.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            vehicle TEXT,
            service TEXT,
            location TEXT,
            address TEXT,
            date TEXT,
            time TEXT,
            notes TEXT
        )
        """)

init_db()

# ---------------- ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        with get_db() as db:
            db.execute("""
                INSERT INTO bookings
                (name, phone, vehicle, service, location, address, date, time, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["name"],
                request.form["phone"],
                request.form["vehicle"],
                request.form["service"],
                request.form["location"],
                request.form["address"],
                request.form["date"],
                request.form["time"],
                request.form.get("notes", "")
            ))
        return redirect("/")

    return render_template_string("""
    <h1>Coastal Gloss Booking</h1>
    <form method="post">
        <input name="name" placeholder="Full Name" required><br><br>
        <input name="phone" placeholder="Phone Number" required><br><br>
        <input name="vehicle" placeholder="Vehicle" required><br><br>

        <label>Service</label><br>
        <select name="service">
            <option>Mobile Detail</option>
            <option>Ceramic Coating</option>
        </select><br><br>

        <label>Location</label><br>
        <select name="location">
            <option>Mobile</option>
            <option>Drop Off</option>
        </select><br><br>

        <label>Address</label><br>
        <input name="address" placeholder="Street, City"><br><br>

        <label>Date</label><br>
        <input type="date" name="date"><br><br>

        <label>Time</label><br>
        <select name="time">
            <option>9:00 AM</option>
            <option>12:00 PM</option>
            <option>3:00 PM</option>
        </select><br><br>

        <textarea name="notes" placeholder="Notes"></textarea><br><br>

        <button type="submit">Book Appointment</button>
    </form>
    """)


@app
