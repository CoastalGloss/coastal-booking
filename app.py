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
            notes TEXT,
            created_at TEXT
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
                (name, phone, vehicle, service, location, date, time, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.form["name"],
                request.form["phone"],
                request.form["vehicle"],
                request.form["service"],
                request.form["location"],
                request.form["date"],
                request.form["time"],
                request.form.get("notes", ""),
                datetime.now().isoformat()
            ))
        return "<h2>Booking submitted successfully!</h2><p>You may close this window.</p>"

    return render_template_string("""
    <h1>Coastal Gloss Booking</h1>
    <form method="post">
        <label>Name</label><br>
        <input name="name" required><br><br>

        <label>Phone</label><br>
        <input name="phone" required><br><br>

        <label>Vehicle</label><br>
        <input name="vehicle" required><br><br>

        <label>Service</label><br>
        <select name="service">
            <option>Exterior Detail - $105</option>
            <option>Interior Detail - $165</option>
            <option>Full Detail - $299</option>
            <option>1 Year Ceramic - $499</option>
            <option>2 Year Ceramic - $749</option>
            <option>5 Year Ceramic - $1499</option>
        </select><br><br>

        <label>Location</label><br>
        <select name="location">
            <option>Mobile</option>
            <option>Drop-Off</option>
        </select><br><br>

        <label>Date</label><br>
        <input type="date" name="date" required><br><br>

        <label>Time</label><br>
        <select name="time">
            <option>9:00 AM</option>
            <option>12:00 PM</option>
            <option>3:00 PM</option>
        </select><br><br>

        <label>Notes</label><br>
        <textarea name="notes"></textarea><br><br>

        <button type="submit">Book Appointment</button>
    </form>
    """)

# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
def admin():
    with get_db() as db:
        rows = db.execute("SELECT * FROM bookings ORDER BY date, time").fetchall()

    html = "<h1>Admin Dashboard</h1>"
    for r in rows:
        html += f"""
        <div style='border:1px solid #ccc; padding:10px; margin-bottom:10px'>
            <strong>{r['name']}</strong> — {r['service']}<br>
            {r['date']} @ {r['time']}<br>
            {r['vehicle']} | {r['location']}<br>
            <em>{r['notes']}</em>
        </div>
        """
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
