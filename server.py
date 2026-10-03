import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session

app = Flask(__name__)
# Session security ke liye secret key
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fsp_super_secret_shield_key_9988")

DATABASE_URL = os.environ.get("DATABASE_URL")[cite: 1]

# ================= ADMIN DASHBOARD PASSWORD =================
# Password Render ke Environment Variables se aayega, GitHub par nazar nahi aayega
ADMIN_DASHBOARD_PASSWORD = os.environ.get("ADMIN_PASSWORD", "shan@786")
# =============================================================

# ================= APP VERSION & AUTO-UPDATER CONFIG =================
CURRENT_APP_VERSION = "1.0.0"
LATEST_EXE_DOWNLOAD_URL = "https://github.com/ryzenx3hack-lgtm/fsp-license-server/releases/latest/download/FirmwareStudioPro.exe"
# ======================================================================

def get_db():[cite: 1]
    if DATABASE_URL:[cite: 1]
        import psycopg2[cite: 1]
        db_url = DATABASE_URL[cite: 1]
        if db_url.startswith("postgres://"):[cite: 1]
            db_url = db_url.replace("postgres://", "postgresql://", 1)[cite: 1]
        conn = psycopg2.connect(db_url)[cite: 1]
        return conn, "postgres"[cite: 1]
    else:
        conn = sqlite3.connect("licenses_persistent.db")[cite: 1]
        return conn, "sqlite"[cite: 1]

def init_db():[cite: 1]
    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    if db_type == "postgres":[cite: 1]
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
        ''')[cite: 1]
        cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS pc_name TEXT DEFAULT '';")[cite: 1]
        cur.execute("ALTER TABLE licenses ADD COLUMN IF NOT EXISTS os_info TEXT DEFAULT '';")[cite: 1]
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
        ''')[cite: 1]
        try:[cite: 1]
            cur.execute("ALTER TABLE licenses ADD COLUMN pc_name TEXT DEFAULT ''")[cite: 1]
        except Exception:[cite: 1]
            pass[cite: 1]
        try:[cite: 1]
            cur.execute("ALTER TABLE licenses ADD COLUMN os_info TEXT DEFAULT ''")[cite: 1]
        except Exception:[cite: 1]
            pass[cite: 1]
    conn.commit()[cite: 1]
    cur.close()[cite: 1]
    conn.close()[cite: 1]

try:[cite: 1]
    init_db()[cite: 1]
except Exception as e:[cite: 1]
    print(f"DB Init Warning: {e}")[cite: 1]

# Admin Login Protection Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin_authenticated"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

HTML_LOGIN = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Authentication Required</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body { 
            background: #080a10; 
            color: #f1f5f9; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 16px;
        }
        .login-card {
            background: #111625;
            border: 1px solid #1f293d;
            border-radius: 12px;
            padding: 28px 24px;
            width: 100%;
            max-width: 380px;
            box-shadow: 0 10px 35px rgba(0,0,0,0.7);
            text-align: center;
        }
        h2 {
            color: #ff2a70;
            margin: 0 0 8px 0;
            font-size: 20px;
            font-weight: 800;
        }
        p {
            color: #94a3b8;
            font-size: 13px;
            margin-bottom: 20px;
        }
        input[type="password"] {
            width: 100%;
            padding: 12px 14px;
            background: #090d16;
            border: 1px solid #283552;
            border-radius: 6px;
            color: #38bdf8;
            font-size: 15px;
            outline: none;
            margin-bottom: 16px;
            text-align: center;
            letter-spacing: 2px;
        }
        input[type="password"]:focus {
            border-color: #38bdf8;
        }
        .btn-submit {
            width: 100%;
            padding: 12px;
            background: #2563eb;
            color: #ffffff;
            font-size: 14px;
            font-weight: 700;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .btn-submit:hover {
            background: #1d4ed8;
        }
        .err-msg {
            color: #ef4444;
            font-size: 12px;
            margin-bottom: 12px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>🔒 Admin Access</h2>
        <p>Enter Master Password to open Manager</p>
        {% if error %}
            <div class="err-msg">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="Enter Password" autofocus required>
            <button type="submit" class="btn-submit">Authenticate & Unlock</button>
        </form>
    </div>
</body>
</html>
"""

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FSP Cloud License Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * { box-sizing: border-box; }
        body { 
            background: #080a10; 
            color: #f1f5f9; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; 
            padding: 14px; 
            margin: 0; 
        }
        .box { 
            background: #111625; 
            border: 1px solid #1f293d; 
            border-radius: 12px; 
            padding: 18px; 
            max-width: 1200px; 
            margin: 0 auto; 
            box-shadow: 0 8px 30px rgba(0,0,0,0.6); 
        }
        
        .header-row { 
            display: flex; 
            flex-wrap: wrap; 
            justify-content: space-between; 
            align-items: center; 
            gap: 12px;
            border-bottom: 1px solid #1f293d; 
            padding-bottom: 14px; 
            margin-bottom: 18px; 
        }
        h1 { 
            color: #ff2a70; 
            margin: 0; 
            font-size: 20px; 
            font-weight: 800;
            letter-spacing: 0.5px;
        }
        .right-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .pulse-live { 
            display: inline-flex; 
            align-items: center; 
            gap: 6px; 
            font-size: 11px; 
            color: #10b981; 
            font-weight: 700;
            background: rgba(16, 185, 129, 0.1);
            padding: 4px 10px;
            border-radius: 20px;
            border: 1px solid rgba(16, 185, 129, 0.25);
        }
        .dot { 
            width: 8px; 
            height: 8px; 
            background-color: #10b981; 
            border-radius: 50%; 
            box-shadow: 0 0 8px #10b981; 
            animation: pulse 1.5s infinite; 
        }
        @keyframes pulse { 
            0% { opacity: 1; transform: scale(1); } 
            50% { opacity: 0.3; transform: scale(0.85); } 
            100% { opacity: 1; transform: scale(1); } 
        }
        .btn-logout {
            background: #252d42;
            color: #cbd5e1;
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none;
            border: 1px solid #3b4866;
        }
        .btn-logout:hover {
            background: #ef4444;
            color: #ffffff;
            border-color: #ef4444;
        }
        
        .gen-bar { 
            display: flex; 
            flex-wrap: wrap; 
            gap: 10px; 
            margin-bottom: 20px; 
            background: #171f33;
            padding: 14px;
            border-radius: 8px;
            align-items: center;
        }
        .gen-label {
            color: #00f2fe; 
            font-weight: 700; 
            font-size: 13px;
        }
        select { 
            flex: 1 1 180px;
            padding: 10px 14px; 
            border-radius: 6px; 
            font-weight: 600; 
            border: 1px solid #2b3552; 
            background: #0f1422; 
            color: #38bdf8; 
            font-size: 14px;
            outline: none;
        }
        .btn-gen { 
            flex: 1 1 180px;
            padding: 11px 16px; 
            border-radius: 6px; 
            font-weight: 700; 
            border: none; 
            font-size: 14px; 
            background: #ff2a70; 
            color: #fff; 
            cursor: pointer; 
            transition: all 0.2s; 
            text-align: center;
        }
        .btn-gen:hover { background: #ff4d88; }
        
        .table-responsive {
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border-radius: 8px;
            border: 1px solid #1f293d;
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            min-width: 780px;
            background: #0d121f;
        }
        th, td { 
            padding: 12px 14px; 
            border-bottom: 1px solid #192235; 
            text-align: left; 
            font-size: 13px; 
            vertical-align: middle;
        }
        th { 
            background: #141b2d; 
            color: #00f2fe; 
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }
        
        .active { color: #10b981; font-weight: 700; font-size: 12px; }
        .inactive { color: #ef4444; font-weight: 700; font-size: 12px; }
        
        .key-wrapper {
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }
        .key-text { 
            color: #00f2fe; 
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; 
            font-size: 13px; 
            font-weight: 700; 
        }
        .btn-copy { 
            background: #10b981; 
            color: #fff; 
            padding: 4px 8px; 
            font-size: 11px; 
            font-weight: 600;
            border-radius: 4px; 
            border: none; 
            cursor: pointer; 
            transition: 0.15s;
        }
        .btn-copy:hover { background: #059669; }
        
        .action-cell {
            white-space: nowrap;
            display: flex;
            gap: 6px;
        }
        .btn-toggle { 
            background: #2563eb; 
            color: #fff; 
            padding: 6px 12px; 
            font-size: 12px; 
            font-weight: 600;
            border-radius: 5px; 
            border: none; 
            cursor: pointer; 
            text-decoration: none;
            display: inline-block;
        }
        .btn-del { 
            background: rgba(239, 68, 68, 0.15); 
            color: #ef4444; 
            border: 1px solid rgba(239, 68, 68, 0.4);
            padding: 6px 12px; 
            font-size: 12px; 
            font-weight: 600;
            border-radius: 5px; 
            cursor: pointer; 
            text-decoration: none;
            display: inline-block;
        }
        .btn-del:hover { background: #ef4444; color: #fff; }
        
        .badge { 
            background: #1a2236; 
            padding: 4px 8px; 
            border-radius: 4px; 
            color: #94a3b8; 
            font-family: ui-monospace, monospace; 
            font-size: 11px; 
            border: 1px solid #283552;
            word-break: break-all;
        }
        .pc-info { color: #38bdf8; font-weight: 600; }
        .os-badge { color: #fbbf24; font-size: 12px; }

        @media (max-width: 600px) {
            body { padding: 8px; }
            .box { padding: 12px; border-radius: 8px; }
            h1 { font-size: 18px; }
            .gen-bar { padding: 10px; }
            select, .btn-gen { flex: 1 1 100%; }
        }
    </style>
    <script>
        function copyKey(keyText, btnElement) {
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(keyText).then(function() {
                    btnElement.innerText = "✓ Copied";
                    btnElement.style.background = "#059669";
                    setTimeout(function() {
                        btnElement.innerText = "📋 Copy";
                        btnElement.style.background = "#10b981";
                    }, 1500);
                });
            } else {
                var textArea = document.createElement("textarea");
                textArea.value = keyText;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    btnElement.innerText = "✓ Copied";
                    setTimeout(function() { btnElement.innerText = "📋 Copy"; }, 1500);
                } catch (err) {
                    alert("Copy failed: " + err);
                }
                document.body.removeChild(textArea);
            }
        }

        function fetchRealtimeData() {
            fetch('/api/keys-data')
                .then(res => {
                    if (res.status === 401) {
                        window.location.href = '/login';
                        return null;
                    }
                    return res.json();
                })
                .then(data => {
                    if (!data) return;
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
                                <div class="key-wrapper">
                                    <span class="key-text">${row.key}</span>
                                    <button class="btn-copy" onclick="copyKey('${row.key}', this)">📋 Copy</button>
                                </div>
                            </td>
                            <td><b>${row.days_valid}</b> Days</td>
                            <td><span class="pc-info">${pcName}</span></td>
                            <td><span class="os-badge">${osInfo}</span></td>
                            <td><span class="badge">${hwid}</span></td>
                            <td>${statusTag}</td>
                            <td>
                                <div class="action-cell">
                                    <a href="/toggle/${row.key}"><button class="btn-toggle">${toggleText}</button></a>
                                    <a href="/delete/${row.key}" onclick="return confirm('Delete this key?');"><button class="btn-del">Delete</button></a>
                                </div>
                            </td>
                        </tr>`;
                    });
                    tbody.innerHTML = html;
                })
                .catch(err => console.error("Sync error:", err));
        }

        setInterval(fetchRealtimeData, 4000);
    </script>
</head>
<body>
    <div class="box">
        <div class="header-row">
            <h1>⚡ FSP Cloud License Manager</h1>
            <div class="right-header">
                <div class="pulse-live">
                    <div class="dot"></div> REALTIME SYNC ACTIVE
                </div>
                <a href="/logout" class="btn-logout">Logout</a>
            </div>
        </div>
        
        <form method="POST" action="/create" class="gen-bar">
            <span class="gen-label">Validity Duration:</span>
            <select name="days">
                <option value="7">7 Days</option>
                <option value="15">15 Days</option>
                <option value="30" selected>30 Days (1 Month)</option>
                <option value="90">90 Days (3 Months)</option>
                <option value="365">365 Days (1 Year)</option>
                <option value="9999">Lifetime</option>
            </select>
            <button type="submit" class="btn-gen">➕ Generate New Key</button>
        </form>

        <div class="table-responsive">
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
                            <div class="key-wrapper">
                                <span class="key-text">{{ row[0] }}</span>
                                <button class="btn-copy" onclick="copyKey('{{ row[0] }}', this)">📋 Copy</button>
                            </div>
                        </td>
                        <td><b>{{ row[4] }}</b> Days</td>
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
                            <div class="action-cell">
                                <a href="/toggle/{{ row[0] }}"><button class="btn-toggle">{{ 'Deactivate' if row[7] else 'Activate' }}</button></a>
                                <a href="/delete/{{ row[0] }}" onclick="return confirm('Delete this key?');"><button class="btn-del">Delete</button></a>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

# ================= AUTHENTICATION ROUTES =================
@app.route("/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if pwd == ADMIN_DASHBOARD_PASSWORD:
            session["is_admin_authenticated"] = True
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid Master Password! Access Denied."
    return render_template_string(HTML_LOGIN, error=error)

@app.route("/logout")
def admin_logout():
    session.pop("is_admin_authenticated", None)
    return redirect(url_for("admin_login"))

# ================= PROTECTED DASHBOARD ROUTES =================
@app.route("/")
@login_required
def dashboard():
    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    cur.execute("SELECT key, hwid, pc_name, os_info, days_valid, created_at, activated_at, is_active FROM licenses ORDER BY created_at DESC")[cite: 1]
    rows = cur.fetchall()[cite: 1]
    cur.close()[cite: 1]
    conn.close()[cite: 1]
    return render_template_string(HTML_DASHBOARD, rows=rows)[cite: 1]

@app.route("/api/keys-data")
def keys_data():
    # Only return keys list if admin session is active
    if not session.get("is_admin_authenticated"):
        return jsonify({"error": "Unauthorized"}), 401

    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    cur.execute("SELECT key, hwid, pc_name, os_info, days_valid, created_at, activated_at, is_active FROM licenses ORDER BY created_at DESC")[cite: 1]
    rows = cur.fetchall()[cite: 1]
    cur.close()[cite: 1]
    conn.close()[cite: 1]
    
    data = [][cite: 1]
    for r in rows:[cite: 1]
        data.append({[cite: 1]
            "key": r[0],[cite: 1]
            "hwid": r[1] or "",[cite: 1]
            "pc_name": r[2] or "",[cite: 1]
            "os_info": r[3] or "",[cite: 1]
            "days_valid": r[4],[cite: 1]
            "is_active": bool(r[7])[cite: 1]
        })
    return jsonify(data)[cite: 1]

@app.route("/create", methods=["POST"])
@login_required
def create_key():
    days = int(request.form.get("days", 30))[cite: 1]
    raw_token = secrets.token_hex(8).upper()[cite: 1]
    key = f"FSP-{raw_token[:4]}-{raw_token[4:8]}-{raw_token[8:12]}-{raw_token[12:]}"[cite: 1]
    now = datetime.utcnow()[cite: 1]
    
    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    if db_type == "postgres":[cite: 1]
        cur.execute("INSERT INTO licenses (key, days_valid, created_at, is_active) VALUES (%s, %s, %s, %s)",[cite: 1]
                    (key, days, now, True))[cite: 1]
    else:
        cur.execute("INSERT INTO licenses (key, days_valid, created_at, is_active) VALUES (?, ?, ?, 1)",[cite: 1]
                    (key, days, now.isoformat()))[cite: 1]
    conn.commit()[cite: 1]
    cur.close()[cite: 1]
    conn.close()[cite: 1]
    return redirect(url_for('dashboard'))[cite: 1]

@app.route("/toggle/<key>")
@login_required
def toggle_status(key):
    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    if db_type == "postgres":[cite: 1]
        cur.execute("UPDATE licenses SET is_active = NOT is_active WHERE key = %s", (key,))[cite: 1]
    else:
        cur.execute("UPDATE licenses SET is_active = CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE key = ?", (key,))[cite: 1]
    conn.commit()[cite: 1]
    cur.close()[cite: 1]
    conn.close()[cite: 1]
    return redirect(url_for('dashboard'))[cite: 1]

@app.route("/delete/<key>")
@login_required
def delete_key(key):
    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    if db_type == "postgres":[cite: 1]
        cur.execute("DELETE FROM licenses WHERE key = %s", (key,))[cite: 1]
    else:
        cur.execute("DELETE FROM licenses WHERE key = ?", (key,))[cite: 1]
    conn.commit()[cite: 1]
    cur.close()[cite: 1]
    conn.close()[cite: 1]
    return redirect(url_for('dashboard'))[cite: 1]

# ================= PUBLIC CLIENT APIS (NO LOGIN REQUIRED) =================
@app.route("/api/check-update")
def check_update():
    return jsonify({
        "latest_version": CURRENT_APP_VERSION,
        "download_url": LATEST_EXE_DOWNLOAD_URL,
        "changelog": "Performance improvements and patch stability."
    })

@app.route("/api/verify-license", methods=["POST"])
def verify_license():
    data = request.get_json(force=True, silent=True) or {}[cite: 1]
    key = data.get("key", "").strip()[cite: 1]
    client_hwid = data.get("hwid", "").strip()[cite: 1]
    pc_name = data.get("pc_name", "").strip()[cite: 1]
    os_info = data.get("os_info", "").strip()[cite: 1]

    if not key or not client_hwid:[cite: 1]
        return jsonify({"valid": False, "message": "Invalid verification payload."}), 400[cite: 1]

    conn, db_type = get_db()[cite: 1]
    cur = conn.cursor()[cite: 1]
    if db_type == "postgres":[cite: 1]
        cur.execute("SELECT hwid, days_valid, activated_at, is_active FROM licenses WHERE key = %s", (key,))[cite: 1]
    else:
        cur.execute("SELECT hwid, days_valid, activated_at, is_active FROM licenses WHERE key = ?", (key,))[cite: 1]
    
    row = cur.fetchone()[cite: 1]
    if not row:[cite: 1]
        cur.close()[cite: 1]
        conn.close()[cite: 1]
        return jsonify({"valid": False, "message": "License key not found in system."}), 404[cite: 1]

    bound_hwid, days_valid, activated_at, is_active = row[cite: 1]

    if not is_active:[cite: 1]
        cur.close()[cite: 1]
        conn.close()[cite: 1]
        return jsonify({"valid": False, "message": "License has been deactivated by administrator."}), 403[cite: 1]

    now = datetime.utcnow()[cite: 1]

    if not bound_hwid:[cite: 1]
        bound_hwid = client_hwid[cite: 1]
        activated_at = now[cite: 1]
        if db_type == "postgres":[cite: 1]
            cur.execute("""
                UPDATE licenses 
                SET hwid = %s, pc_name = %s, os_info = %s, activated_at = %s 
                WHERE key = %s
            """, (client_hwid, pc_name, os_info, now, key))[cite: 1]
        else:
            cur.execute("""
                UPDATE licenses 
                SET hwid = ?, pc_name = ?, os_info = ?, activated_at = ? 
                WHERE key = ?
            """, (client_hwid, pc_name, os_info, now.isoformat(), key))[cite: 1]
        conn.commit()[cite: 1]
    else:
        if db_type == "postgres":[cite: 1]
            cur.execute("UPDATE licenses SET pc_name = COALESCE(NULLIF(pc_name, ''), %s), os_info = COALESCE(NULLIF(os_info, ''), %s) WHERE key = %s", (pc_name, os_info, key))[cite: 1]
        else:
            cur.execute("UPDATE licenses SET pc_name = CASE WHEN pc_name='' THEN ? ELSE pc_name END, os_info = CASE WHEN os_info='' THEN ? ELSE os_info END WHERE key = ?", (pc_name, os_info, key))[cite: 1]
        conn.commit()[cite: 1]

    if bound_hwid != client_hwid:[cite: 1]
        cur.close()[cite: 1]
        conn.close()[cite: 1]
        return jsonify({"valid": False, "message": "License is locked to a different computer!"}), 403[cite: 1]

    if isinstance(activated_at, str):[cite: 1]
        activated_at = datetime.fromisoformat(activated_at)[cite: 1]
    
    expiry_date = activated_at + timedelta(days=days_valid)[cite: 1]
    days_left = max(0, (expiry_date - now).days)[cite: 1]

    if now > expiry_date:[cite: 1]
        cur.close()[cite: 1]
        conn.close()[cite: 1]
        return jsonify({"valid": False, "message": "License subscription has expired."}), 403[cite: 1]

    cur.close()[cite: 1]
    conn.close()[cite: 1]
    return jsonify({[cite: 1]
        "valid": True,[cite: 1]
        "message": "License is valid and verified.",[cite: 1]
        "days_left": days_left[cite: 1]
    }), 200[cite: 1]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)[cite: 1]
