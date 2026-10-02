import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string, redirect, url_for

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    if DATABASE_URL:
        import psycopg2
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url)
        return conn, "postgres"
    else:
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
                pc_name TEXT DEFAULT '',
                os_info TEXT DEFAULT '',
                days_valid INTEGER,
                created_at TIMESTAMP,
                activated_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
        ''')
        cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS pc_name TEXT DEFAULT '';")
        cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS os_info TEXT DEFAULT '';")
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                hwid TEXT DEFAULT '',
                pc_name TEXT DEFAULT '',
                os_info TEXT DEFAULT '',
                days_valid INTEGER,
                created_at TEXT,
                activated_at TEXT,
                is_active INTEGER DEFAULT 1
            );
        ''')
        try:
            cur.execute("ALTER TABLE licenses ADD COLUMN pc_name TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            cur.execute("ALTER TABLE licenses ADD COLUMN os_info TEXT DEFAULT ''")
        except Exception:
            pass
    conn.commit()
    cur.close()
    conn.close()

try:
    init_db()
except Exception as e:
    print(f"DB Init Warning: {e}")

HTML_DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>FSP Cloud License Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background: #0b0d17; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 25px; margin: 0; }
        .box { background: #131827; border: 1px solid #2b3552; border-radius: 8px; padding: 20px; max-width: 1200px; margin: 0 auto; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .header-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2b3552; padding-bottom: 12px; margin-bottom: 15px; }
        h1 { color: #ff2a70; margin: 0; font-size: 24px; }
        .pulse-live { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #10b981; font-weight: bold; }
        .dot { width: 10px; height: 10px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.9); } 100% { opacity: 1; transform: scale(1); } }
        
        .gen-bar { display: flex; gap: 10px; margin-bottom: 20px; align-items: center; }
        select, button { padding: 10px 15px; border-radius: 5px; font-weight: bold; border: none; font-size: 14px; }
        select { background: #1c2337; color: #00f2fe; border: 1px solid #2b3552; }
        button { background: #ff2a70; color: #fff; cursor: pointer; transition: 0.2s; }
        button:hover { background: #ff4d88; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 10px; border-bottom: 1px solid #2b3552; text-align: left; font-size: 13px; }
        th { background: #1c2337; color: #00f2fe; }
        .active { color: #10b981; font-weight: bold; }
        .inactive { color: #ef4444; font-weight: bold; }
        .btn-copy { background: #10b981; color: #fff; padding: 4px 8px; font-size: 11px; margin-left: 6px; border-radius: 4px; border: none; cursor: pointer; }
        .btn-copy:hover { background: #059669; }
        .btn-toggle { background: #2563eb; color: #fff; padding: 5px 10px; font-size: 12px; border-radius: 4px; border: none; cursor: pointer; }
        .btn-del { background: #ef4444; color: #fff; padding: 5px 10px; font-size: 12px; margin-left: 5px; border-radius: 4px; border: none; cursor: pointer; }
        .badge { background: #1c2337; padding: 3px 6px; border-radius: 4px; color: #94a3b8; font-family: monospace; font-size: 11px; }
        .pc-info { color: #38bdf8; font-weight: bold; }
        .os-badge { color: #fbbf24; font-size: 12px; }
        .key-text { color: #00f2fe; font-family: monospace; font-size: 13px; font-weight: bold; }
    </style>
    <script>
        function copyKey(keyText, btnElement) {
            navigator.clipboard.writeText(keyText).then(function() {
                var originalText = btnElement.innerText;
                btnElement.innerText = "Copied!";
                btnElement.style.background = "#059669";
                setTimeout(function() {
                    btnElement.innerText = originalText;
                    btnElement.style.background = "#10b981";
                }, 1500);
            }).catch(function(err) {
                alert("Failed to copy key: " + err);
            });
        }

        // Realtime Table Auto-Updater (Polling every 4 seconds)
        function fetchRealtimeData() {
            fetch('/api/keys-data')
                .then(res => res.json())
                .then(data => {
                    var tbody = document.getElementById("table-body");
                    var html = "";
                    data.forEach(row => {
                        var statusTag = row.is_active 
                            ? '<span class="active">ACTIVE</span>' 
                            : '<span class="inactive">DEACTIVATED</span>';
                        var toggleText = row.is_active ? 'Deactivate' : 'Activate';
                        var pcName = row.pc_name ? row.pc_name : 'Not Connected';
                        var osInfo = row.os_info ? row.os_info : '--';
                        var hwid = row.hwid ? row.hwid : 'Unbound';

                        html += `<tr>
                            <td>
                                <span class="key-text">${row.key}</span>
                                <button class="btn-copy" onclick="copyKey('${row.key}', this)">📋 Copy</button>
                            </td>
                            <td>${row.days_valid} Days</td>
                            <td><span class="pc-info">${pcName}</span></td>
                            <td><span class="os-badge">${osInfo}</span></td>
                            <td><span class="badge">${hwid}</span></td>
                            <td>${statusTag}</td>
                            <td>
                                <a href="/toggle/${row.key}"><button class="btn-toggle">${toggleText}</button></a>
                                <a href="/delete/${row.key}" onclick="return confirm('Delete this key?');"><button class="btn-del">Delete</button></a>
                            </td>
                        </tr>`;
                    });
                    tbody.innerHTML = html;
                })
                .catch(err => console.error("Realtime sync error:", err));
        }

        // Start Auto-Sync
        setInterval(fetchRealtimeData, 4000);
    </script>
</head>
<body>
    <div class="box">
        <div class="header-row">
            <h1>⚡ FSP Cloud License Manager</h1>
            <div class="pulse-live">
                <div class="dot"></div> REALTIME SYNC ACTIVE
            </div>
        </div>
        
        <form method="POST" action="/create" class="gen-bar">
            <label style="color:#00f2fe; font-weight: bold;">Validity Duration:</label>
            <select name="days">
                <option value="7">7 Days</option>
                <option value="15">15 Days</option>
                <option value="30" selected>30 Days (1 Month)</option>
                <option value="90">90 Days (3 Months)</option>
                <option value="365">365 Days (1 Year)</option>
                <option value="9999">Lifetime</option>
            </select>
            <button type="submit">➕ Generate New Key</button>
        </form>

        <table>
            <thead>
                <tr>
                    <th>License Key</th>
                    <th>Validity</th>
                    <th>PC Name / User</th>
                    <th>OS Version</th>
                    <th>Hardware ID (HWID)</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="table-body">
                {% for row in rows %}
                <tr>
                    <td>
                        <span class="key-text">{{ row[0] }}</span>
                        <button class="btn-copy" onclick="copyKey('{{ row[0] }}', this)">📋 Copy</button>
                    </td>
                    <td>{{ row[4] }} Days</td>
                    <td><span class="pc-info">{{ row[2] if row[2] else 'Not Connected' }}</span></td>
                    <td><span class="os-badge">{{ row[3] if row[3] else '--' }}</span></td>
                    <td><span class="badge">{{ row[1] if row[1] else 'Unbound' }}</span></td>
                    <td>
                        {% if row[7] %}
                            <span class="active">ACTIVE</span>
                        {% else %}
                            <span class="inactive">DEACTIVATED</span>
                        {% endif %}
                    </td>
                    <td>
                        <a href="/toggle/{{ row[0] }}"><button class="btn-toggle">{{ 'Deactivate' if row[7] else 'Activate' }}</button></a>
                        <a href="/delete/{{ row[0] }}" onclick="return confirm('Delete this key?');"><button class="btn-del">Delete</button></a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@app.route("/")
def dashboard():
    conn, db_type = get_db()
    cur = conn.cursor()
    cur.execute("SELECT key, hwid, pc_name, os_info, days_valid, created_at, activated_at, is_active FROM licenses ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(HTML_DASHBOARD, rows=rows)

# REALTIME JSON ENDPOINT FOR LIVE AUTO-SYNC
@app.route("/api/keys-data")
def keys_data():
    conn, db_type = get_db()
    cur = conn.cursor()
    cur.execute("SELECT key, hwid, pc_name, os_info, days_valid, created_at, activated_at, is_active FROM licenses ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    data = []
    for r in rows:
        data.append({
            "key": r[0],
            "hwid": r[1] or "",
            "pc_name": r[2] or "",
            "os_info": r[3] or "",
            "days_valid": r[4],
            "is_active": bool(r[7])
        })
    return jsonify(data)

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
    return redirect(url_for('dashboard'))

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
    return redirect(url_for('dashboard'))

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
    return redirect(url_for('dashboard'))

@app.route("/api/verify-license", methods=["POST"])
def verify_license():
    data = request.get_json(force=True, silent=True) or {}
    key = data.get("key", "").strip()
    client_hwid = data.get("hwid", "").strip()
    pc_name = data.get("pc_name", "").strip()
    os_info = data.get("os_info", "").strip()

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

    if not bound_hwid:
        bound_hwid = client_hwid
        activated_at = now
        if db_type == "postgres":
            cur.execute("""
                UPDATE licenses 
                SET hwid = %s, pc_name = %s, os_info = %s, activated_at = %s 
                WHERE key = %s
            """, (client_hwid, pc_name, os_info, now, key))
        else:
            cur.execute("""
                UPDATE licenses 
                SET hwid = ?, pc_name = ?, os_info = ?, activated_at = ? 
                WHERE key = ?
            """, (client_hwid, pc_name, os_info, now.isoformat(), key))
        conn.commit()
    else:
        if db_type == "postgres":
            cur.execute("UPDATE licenses SET pc_name = COALESCE(NULLIF(pc_name, ''), %s), os_info = COALESCE(NULLIF(os_info, ''), %s) WHERE key = %s", (pc_name, os_info, key))
        else:
            cur.execute("UPDATE licenses SET pc_name = CASE WHEN pc_name='' THEN ? ELSE pc_name END, os_info = CASE WHEN os_info='' THEN ? ELSE os_info END WHERE key = ?", (pc_name, os_info, key))
        conn.commit()

    if bound_hwid != client_hwid:
        cur.close()
        conn.close()
        return jsonify({"valid": False, "message": "License is locked to a different computer!"}), 403

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
