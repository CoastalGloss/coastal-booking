import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, render_template_string

app = Flask(__name__)
app.secret_key = "coastal-gloss-secret"

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "/tmp"), "bookings.db")

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

# ---------------- BOOKING PAGE ----------------
@app.route("/", methods=["GET", "POST"])
def booking():
    if request.method == "POST":
        with get_db() as db:
            db.execute("""
                INSERT INTO bookings
                (name, phone, vehicle, service, location, date, time, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["name"],
                request.form["phone"],
                request.form["vehicle"],
                request.form["service"],
                request.form["location"],
                request.form["date"],
                request.form["time"],
                request.form.get("notes", "")
            ))
        return "<h2>Booking submitted successfully!</h2><p>You may close this window.</p>"

    return render_template_string("""
    <h1>Coastal Gloss Booking</h1>
    <form method="post">
        <input name="name" placeholder="Full Name" required><br><br>
        <input name="phone" placeholder="Phone Number" required><br><br>
        <input name="vehicle" placeholder="Vehicle" required><br><br>

        <label>Service</label>
        <select name="service">
            <option>Exterior Detail</option>
            <option>Interior Detail</option>
            <option>Full Detail</option>
            <option>1-Year Ceramic</option>
            <option>2-Year Ceramic</option>
        </select><br><br>

        <label>Location</label>
        <select name="location">
            <option>Mobile</option>
            <option>Drop-Off</option>
        </select><br><br>

        <label>Date</label>
        <input type="date" name="date" required><br><br>

        <label>Time</label>
        <select name="time">
            <option>9:00 AM</option>
            <option>12:00 PM</option>
            <option>3:00 PM</option>
        </select><br><br>

        <label>Notes</label>
        <textarea name="notes"></textarea><br><br>

        <button type="submit">Book Appointment</button>
    </form>
    """)

# ---------------- CALENDAR VIEW ----------------
@app.route("/calendar")
def calendar():
    with get_db() as db:
        rows = db.execute("""
            SELECT * FROM bookings
            ORDER BY date ASC, time ASC
        """).fetchall()

    html = "<h1>Booking Calendar</h1>"

    current_date = None
    for r in rows:
        if r["date"] != current_date:
            html += f"<h2>{r['date']}</h2>"
            current_date = r["date"]

        html += f"""
        <div style='margin-left:20px; padding:8px; border-bottom:1px solid #ddd'>
            <b>{r['time']}</b> — {r['name']} ({r['service']})<br>
            {r['vehicle']} | {r['location']}
        </div>
        """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
