import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Render PostgreSQL URL (Environment variable se uthayega)
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL:
        import psycopg2
        # Render postgres:// ko postgresql:// standard me fix karein agar zaroorat ho
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url)
        return conn, "postgres"
    else:
        # Fallback local sqlite
        conn = sqlite3.connect("licenses_persistent.db")
        return conn, "sqlite"

def init_db():
    conn, db_type = get_db()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                hwid TEXT DEFAULT '',
                days_valid INTEGER,
                created_at TIMESTAMP,
                activated_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                hwid TEXT DEFAULT '',
                days_valid INTEGER,
                created_at TEXT,
                activated_at TEXT,
                is_active INTEGER DEFAULT 1
            );
        ''')
    conn.commit()
    cur.close()
    conn.close()

# Initialize DB on startup
try:
    init_db()
except Exception as e:
    print(f"DB Init Warning: {e}")

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>FSP Cloud License Manager</title>
    <style>
        body { background: #0b0d17; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 25px; margin: 0; }
        .box { background: #131827; border: 1px solid #2b3552; border-radius: 8px; padding: 20px; max-width: 950px; margin: 0 auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        h1 { color: #ff2a70; margin-top: 0; }
        .gen-bar { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
        select, button { padding: 10px 15px; border-radius: 5px; font-weight: bold; border: none; font-size: 14px; }
        select { background: #1c2337; color: #00f2fe; border: 1px solid #2b3552; }
        button { background: #ff2a70; color: #fff; cursor: pointer; transition: 0.2s; }
        button:hover { background: #ff4d88; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; border-bottom: 1px solid #2b3552; text-align: left; font-size: 13px; }
        th { background: #1c2337; color: #00f2fe; }
        .active { color: #10b981; font-weight: bold; }
        .inactive { color: #ef4444; font-weight: bold; }
        .btn-toggle { background: #2563eb; padding: 5px 10px; font-size: 12px; }
        .btn-del { background: #ef4444; padding: 5px 10px; font-size: 12px; margin-left: 5px; }
        .badge { background: #1c2337; padding: 3px 8px; border-radius: 4px; color: #94a3b8; font-family: monospace; }
    </style>
</head>
<body>
    <div class="box">
        <h1>⚡ FSP Cloud License Manager</h1>
        <p style="color: #94a3b8;">Persistent Cloud Storage: Active & Protected against restarts.</p>
        
        <form method="POST" action="/create" class="gen-bar">
            <label style="color:#00f2fe; font-weight: bold;">Validity Duration:</label>
            <select name="days">
                <option value="7">7 Days</option>
                <option value="15">15 Days</option>
                <option value="30" selected>30 Days (1 Month)</option>
                <option value="90">90 Days (3 Months)</option>
                <option value="365">365 Days (1 Year)</option>
                <option value="9999">Lifetime (Permanent)</option>
            </select>
            <button type="submit">➕ Generate New Key</button>
        </form>

        <table>
            <tr>
                <th>License Key</th>
                <th>Validity</th>
                <th>Bound HWID</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
            {% for row in rows %}
            <tr>
                <td><b style="color: #00f2fe; font-family: monospace;">{{ row[0] }}</b></td>
                <td>{{ row[2] }} Days</td>
                <td><span class="badge">{{ row[1] if row[1] else 'Unbound (Ready)' }}</span></td>
                <td>
                    {% if row[5] %}
                        <span class="active">ACTIVE</span>
                    {% else %}
                        <span class="inactive">DEACTIVATED</span>
                    {% endif %}
                </td>
                <td>
                    <a href="/toggle/{{ row[0] }}"><button class="btn-toggle">{{ 'Deactivate' if row[5] else 'Activate' }}</button></a>
                    <a href="/delete/{{ row[0] }}" onclick="return confirm('Pakka delete karna hai?');"><button class="btn-del">Delete</button></a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    conn, db_type = get_db()
    cur = conn.cursor()
    cur.execute("SELECT key, hwid, days_valid, created_at, activated_at, is_active FROM licenses ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(HTML_DASHBOARD, rows=rows)

@app.route("/create", methods=["POST"])
def create_key():
    days = int(request.form.get("days", 30))
    raw_token = secrets.token_hex(8).upper()
    key = f"FSP-{raw_token[:4]}-{raw_token[4:8]}-{raw_token[8:12]}-{raw_token[12:]}"
    now = datetime.utcnow()
    
    conn, db_type = get_db()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute("INSERT INTO licenses (key, days_valid, created_at, is_active) VALUES (%s, %s, %s, %s)",
                    (key, days, now, True))
    else:
        cur.execute("INSERT INTO licenses (key, days_valid, created_at, is_active) VALUES (?, ?, ?, 1)",
                    (key, days, now.isoformat()))
    conn.commit()
    cur.close()
    conn.close()
    return dashboard()

@app.route("/toggle/<key>")
def toggle_status(key):
    conn, db_type = get_db()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute("UPDATE licenses SET is_active = NOT is_active WHERE key = %s", (key,))
    else:
        cur.execute("UPDATE licenses SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE key = ?", (key,))
    conn.commit()
    cur.close()
    conn.close()
    return dashboard()

@app.route("/delete/<key>")
def delete_key(key):
    conn, db_type = get_db()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute("DELETE FROM licenses WHERE key = %s", (key,))
    else:
        cur.execute("DELETE FROM licenses WHERE key = ?", (key,))
    conn.commit()
    cur.close()
    conn.close()
    return dashboard()

@app.route("/api/verify-license", methods=["POST"])
def verify_license():
    data = request.get_json(force=True, silent=True) or {}
    key = data.get("key", "").strip()
    client_hwid = data.get("hwid", "").strip()

    if not key or not client_hwid:
        return jsonify({"valid": False, "message": "Invalid verification payload."}), 400

    conn, db_type = get_db()
    cur = conn.cursor()
    if db_type == "postgres":
        cur.execute("SELECT hwid, days_valid, activated_at, is_active FROM licenses WHERE key = %s", (key,))
    else:
        cur.execute("SELECT hwid, days_valid, activated_at, is_active FROM licenses WHERE key = ?", (key,))
    
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return jsonify({"valid": False, "message": "License key not found in system."}), 404

    bound_hwid, days_valid, activated_at, is_active = row

    if not is_active:
        cur.close()
        conn.close()
        return jsonify({"valid": False, "message": "License has been deactivated by administrator."}), 403

    now = datetime.utcnow()

    # First time activation: Bind HWID
    if not bound_hwid:
        bound_hwid = client_hwid
        activated_at = now
        if db_type == "postgres":
            cur.execute("UPDATE licenses SET hwid = %s, activated_at = %s WHERE key = %s", (client_hwid, now, key))
        else:
            cur.execute("UPDATE licenses SET hwid = ?, activated_at = ? WHERE key = ?", (client_hwid, now.isoformat(), key))
        conn.commit()

    # HWID Mismatch check
    if bound_hwid != client_hwid:
        cur.close()
        conn.close()
        return jsonify({"valid": False, "message": "License is locked to a different computer!"}), 403

    # Expiry Check
    if isinstance(activated_at, str):
        activated_at = datetime.fromisoformat(activated_at)
    
    expiry_date = activated_at + timedelta(days=days_valid)
    days_left = max(0, (expiry_date - now).days)

    if now > expiry_date:
        cur.close()
        conn.close()
        return jsonify({"valid": False, "message": "License subscription has expired."}), 403

    cur.close()
    conn.close()
    return jsonify({
        "valid": True,
        "message": "License is valid and verified.",
        "days_left": days_left
    }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
