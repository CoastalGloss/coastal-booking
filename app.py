import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, redirect, url_for, render_template_string, flash

# Optional Twilio SMS (paid service). Set env vars to enable:
# TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
# If not set, the app will just show the confirmation message to copy/paste.
try:
    from twilio.rest import Client
except Exception:
    Client = None

APP_TITLE = "Coastal Gloss — Internal Booking"
DB_PATH = os.path.join(os.path.dirname(__file__), "bookings.db")

TIME_SLOTS = ["09:00", "12:00", "15:00"]  # 9am, 12pm, 3pm (24h format)
SERVICE_DETAIL = "Mobile Detail (3 hours)"
SERVICE_COATING = "Ceramic Coating (24 hours)"

LOCATION_MOBILE = "Mobile (Customer Location)"
LOCATION_SHOP = "Shop Drop-Off"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT,
                vehicle TEXT NOT NULL,
                service_type TEXT NOT NULL,
                location_type TEXT NOT NULL,
                date TEXT NOT NULL,       -- YYYY-MM-DD
                slot TEXT NOT NULL,       -- HH:MM
                status TEXT NOT NULL DEFAULT 'New',  -- New/Confirmed/Cancelled/Completed
                notes TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_booking_date_slot ON bookings(date, slot);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_booking_status ON bookings(status);")


def normalize_phone(phone: str) -> str:
    # Very light cleanup; you can tighten later
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+").strip()


def slot_label(hhmm: str) -> str:
    if hhmm == "09:00":
        return "9:00 AM"
    if hhmm == "12:00":
        return "12:00 PM"
    if hhmm == "15:00":
        return "3:00 PM"
    return hhmm


def date_label(yyyy_mm_dd: str) -> str:
    try:
        return datetime.strptime(yyyy_mm_dd, "%Y-%m-%d").strftime("%a, %b %d, %Y")
    except Exception:
        return yyyy_mm_dd


def is_slot_available(date_str: str, slot: str, service_type: str) -> (bool, str):
    """
    Rules:
    - Mobile detail blocks only its time slot.
    - Coating blocks 9am + 12pm + 3pm on that date.
    - HOWEVER: You can still book ONE 3pm detail on a coating day.
      So if a coating exists on that date:
         - 9am and 12pm are unavailable for details
         - 3pm detail is allowed if no other 3pm detail already exists
    - If any detail exists on slot, can't double-book that slot.
    - If coating exists on date, can't book another coating that date.
    """
    with db() as conn:
        existing = conn.execute(
            "SELECT service_type, slot, status FROM bookings WHERE date = ? AND status != 'Cancelled'",
            (date_str,)
        ).fetchall()

    # Any coating already booked that day?
    coating_exists = any(r["service_type"] == SERVICE_COATING for r in existing)
    coating_booking = next((r for r in existing if r["service_type"] == SERVICE_COATING), None)

    # Slot already booked by a detail?
    slot_taken_by_detail = any((r["service_type"] == SERVICE_DETAIL and r["slot"] == slot) for r in existing)

    # Another coating same day?
    if service_type == SERVICE_COATING:
        if coating_exists:
            return False, "A ceramic coating is already booked for that date."
        # Disallow if you already have details earlier that would conflict? (Optional)
        # We'll allow it (you said you can still handle a detail same day as coating).
        return True, ""

    # Service is detail
    if slot_taken_by_detail:
        return False, "That time slot is already booked."

    if coating_exists:
        if slot in ("09:00", "12:00"):
            return False, "A ceramic coating is booked that day — only the 3:00 PM detail slot is available."
        # slot is 15:00
        # Allow only one 3pm detail (already ensured slot_taken_by_detail is False)
        return True, ""

    return True, ""


def send_sms(to_phone: str, message: str) -> (bool, str):
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_FROM_NUMBER")

    if not (sid and token and from_num and Client):
        return False, "Twilio not configured — copy/paste the text instead."

    try:
        client = Client(sid, token)
        client.messages.create(
            body=message,
            from_=from_num,
            to=to_phone
        )
        return True, "Text sent."
    except Exception as e:
        return False, f"Text failed: {e}"


BOOK_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{{title}}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 820px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin: 16px 0; }
    label { display:block; margin-top: 10px; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 10px; margin-top: 6px; border-radius: 10px; border: 1px solid #ccc; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .btn { margin-top: 14px; padding: 12px 14px; border: 0; border-radius: 12px; background: #111; color: #fff; cursor:pointer; }
    .muted { color:#666; font-size: 0.95em; }
    .flash { background:#fff7d6; border:1px solid #f0d46a; padding:10px; border-radius: 10px; margin: 10px 0; }
    a { color:#0b57d0; text-decoration:none; }
  </style>
</head>
<body>
  <h1>{{title}}</h1>
  <p class="muted">Private internal booking page. Use this yourself, or send it to clients if you want.</p>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}
        <div class="flash">{{m}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class="card">
    <h2>New Booking</h2>
    <form method="post" action="/book">
      <div class="row">
        <div>
          <label>Full Name*</label>
          <input name="name" required />
        </div>
        <div>
          <label>Phone Number (for text)*</label>
          <input name="phone" required placeholder="228-xxx-xxxx" />
        </div>
      </div>

      <label>Vehicle (Year / Make / Model)*</label>
      <input name="vehicle" required placeholder="2024 Tahoe" />

      <div class="row">
        <div>
          <label>Service Type*</label>
          <select name="service_type" required>
            <option value="{{SERVICE_DETAIL}}">{{SERVICE_DETAIL}}</option>
            <option value="{{SERVICE_COATING}}">{{SERVICE_COATING}}</option>
          </select>
        </div>
        <div>
          <label>Location Type*</label>
          <select name="location_type" required>
            <option value="{{LOCATION_MOBILE}}">{{LOCATION_MOBILE}}</option>
            <option value="{{LOCATION_SHOP}}">{{LOCATION_SHOP}}</option>
          </select>
        </div>
      </div>

      <label>Address (required for Mobile)</label>
      <input name="address" placeholder="Street, City" />

      <div class="row">
        <div>
          <label>Date*</label>
          <input type="date" name="date" required />
        </div>
        <div>
          <label>Time Slot*</label>
          <select name="slot" required>
            {% for s in TIME_SLOTS %}
              <option value="{{s}}">{{slot_label(s)}}</option>
            {% endfor %}
          </select>
        </div>
      </div>

      <label>Notes</label>
      <textarea name="notes" rows="3" placeholder="Gate code, heavy pet hair, etc."></textarea>

      <button class="btn" type="submit">Create Booking</button>
    </form>
  </div>

  <div class="card">
    <h2>Admin</h2>
    <p class="muted">View and manage bookings: <a href="/admin">Open Admin Dashboard</a></p>
  </div>
</body>
</html>
"""

ADMIN_PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Admin — {{title}}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 1100px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #eee; padding: 10px; text-align:left; vertical-align: top; }
    th { background: #fafafa; }
    .pill { display:inline-block; padding:4px 10px; border-radius: 999px; font-size: 0.9em; border:1px solid #ddd; }
    .btn { padding: 8px 10px; border:0; border-radius: 10px; cursor:pointer; margin-right: 6px; }
    .ok { background:#111; color:#fff; }
    .bad { background:#eee; }
    .flash { background:#fff7d6; border:1px solid #f0d46a; padding:10px; border-radius: 10px; margin: 10px 0; }
    a { color:#0b57d0; text-decoration:none; }
  </style>
</head>
<body>
  <h1>Admin — {{title}}</h1>
  <p><a href="/">← Back to Booking Page</a></p>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}
        <div class="flash">{{m}}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <table>
    <thead>
      <tr>
        <th>Date / Time</th>
        <th>Customer</th>
        <th>Service</th>
        <th>Location</th>
        <th>Status</th>
        <th>Notes</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for b in bookings %}
      <tr>
        <td>
          <div><strong>{{date_label(b["date"])}}</strong></div>
          <div>{{slot_label(b["slot"])}}</div>
        </td>
        <td>
          <div><strong>{{b["name"]}}</strong></div>
          <div>{{b["phone"]}}</div>
          {% if b["address"] %}<div class="muted">{{b["address"]}}</div>{% endif %}
          <div class="muted">{{b["vehicle"]}}</div>
        </td>
        <td>{{b["service_type"]}}</td>
        <td>{{b["location_type"]}}</td>
        <td><span class="pill">{{b["status"]}}</span></td>
        <td>{{b["notes"] or ""}}</td>
        <td>
          <form method="post" action="/status" style="display:inline;">
            <input type="hidden" name="id" value="{{b['id']}}">
            <input type="hidden" name="status" value="Confirmed">
            <button class="btn ok" type="submit">Confirm + Text</button>
          </form>
          <form method="post" action="/status" style="display:inline;">
            <input type="hidden" name="id" value="{{b['id']}}">
            <input type="hidden" name="status" value="Cancelled">
            <button class="btn bad" type="submit">Cancel</button>
          </form>
          <form method="post" action="/status" style="display:inline;">
            <input type="hidden" name="id" value="{{b['id']}}">
            <input type="hidden" name="status" value="Completed">
            <button class="btn bad" type="submit">Complete</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


@app.get("/")
def home():
    return render_template_string(
        BOOK_PAGE,
        title=APP_TITLE,
        TIME_SLOTS=TIME_SLOTS,
        SERVICE_DETAIL=SERVICE_DETAIL,
        SERVICE_COATING=SERVICE_COATING,
        LOCATION_MOBILE=LOCATION_MOBILE,
        LOCATION_SHOP=LOCATION_SHOP,
        slot_label=slot_label
    )


@app.post("/book")
def book():
    name = request.form.get("name", "").strip()
    phone = normalize_phone(request.form.get("phone", ""))
    vehicle = request.form.get("vehicle", "").strip()
    service_type = request.form.get("service_type", "").strip()
    location_type = request.form.get("location_type", "").strip()
    address = request.form.get("address", "").strip()
    date_str = request.form.get("date", "").strip()
    slot = request.form.get("slot", "").strip()
    notes = request.form.get("notes", "").strip()

    if not name or not phone or not vehicle or not date_str or slot not in TIME_SLOTS:
        flash("Missing required fields.")
        return redirect(url_for("home"))

    if location_type == LOCATION_MOBILE and not address:
        flash("Address is required for Mobile service.")
        return redirect(url_for("home"))

    ok, reason = is_slot_available(date_str, slot, service_type)
    if not ok:
        flash(f"Not available: {reason}")
        return redirect(url_for("home"))

    with db() as conn:
        conn.execute("""
            INSERT INTO bookings (created_at, name, phone, address, vehicle, service_type, location_type, date, slot, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            name, phone, address, vehicle, service_type, location_type, date_str, slot, notes
        ))

    flash("Booking created. Open Admin to confirm + text them.")
    return redirect(url_for("home"))


@app.get("/admin")
def admin():
    with db() as conn:
        bookings = conn.execute("""
            SELECT * FROM bookings
            WHERE status != 'Cancelled'
            ORDER BY date ASC, slot ASC
        """).fetchall()

    return render_template_string(
        ADMIN_PAGE,
        title=APP_TITLE,
        bookings=bookings,
        slot_label=slot_label,
        date_label=date_label
    )


@app.post("/status")
def set_status():
    booking_id = request.form.get("id", "").strip()
    status = request.form.get("status", "").strip()

    if status not in ("Confirmed", "Cancelled", "Completed"):
        flash("Invalid status.")
        return redirect(url_for("admin"))

    with db() as conn:
        b = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
        if not b:
            flash("Booking not found.")
            return redirect(url_for("admin"))

        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))

    if status == "Confirmed":
        msg = (
            f"Hey {b['name']}! This is Caleb with Coastal Gloss 👋\n"
            f"You're confirmed for {b['service_type']} on {date_label(b['date'])} at {slot_label(b['slot'])}.\n"
            f"Reply here if anything changes."
        )
        sent, info = send_sms(b["phone"], msg)
        if sent:
            flash("Confirmed and text sent ✅")
        else:
            flash(f"Confirmed ✅ (SMS not sent: {info}) — Copy/paste this text:\n{msg}")

    else:
        flash(f"Updated status to {status}.")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
