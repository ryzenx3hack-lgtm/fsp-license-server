import os
import json
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_FILE = "keys_db.json"
ADMIN_CONTACT_NUMBER = "03493189460"

ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FSP License Management Console</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #0b0d17; color: #f8fafc; padding: 25px; }
        .container { max-width: 1050px; margin: auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #232b3e; padding-bottom: 15px; margin-bottom: 20px; }
        .header h1 { font-size: 20px; color: #ff2a70; }
        .live-tag { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #10b981; font-weight: bold; }
        .live-dot { width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; }
        .card { background: #131827; border: 1px solid #232b3e; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .card h2 { font-size: 15px; margin-bottom: 12px; color: #00f2fe; }
        .gen-box { display: flex; gap: 10px; align-items: center; }
        select, button { padding: 9px 14px; border-radius: 6px; border: 1px solid #2b3552; background: #1c2337; color: #fff; font-size: 13px; outline: none; }
        button.btn-primary { background: #ff2a70; border-color: #ff2a70; font-weight: bold; cursor: pointer; transition: 0.2s; }
        button.btn-primary:hover { background: #ff4d88; }
        .key-result { margin-top: 15px; padding: 12px; background: #1c2337; border-left: 4px solid #00f2fe; border-radius: 4px; display: none; align-items: center; justify-content: space-between; }
        .key-text { font-family: 'Consolas', monospace; font-size: 17px; color: #00f2fe; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #1c2337; vertical-align: middle; }
        th { color: #94a3b8; font-size: 11px; text-transform: uppercase; }
        .key-mono { font-family: 'Consolas', monospace; font-weight: bold; color: #f8fafc; }
        .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; display: inline-block; }
        .badge-active { background: rgba(16, 185, 129, 0.2); color: #10b981; }
        .badge-expired { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
        .badge-pending { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
        .badge-disabled { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
        .action-btns { display: flex; gap: 6px; }
        .btn-sm { padding: 5px 10px; font-size: 12px; border-radius: 4px; border: none; cursor: pointer; font-weight: 600; }
        .btn-copy-sm { background: #232b3e; color: #00f2fe; border: 1px solid #2b3552; }
        .btn-copy-sm:hover { background: #2d374d; }
        .btn-toggle-deact { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
        .btn-toggle-deact:hover { background: #f59e0b; color: #000; }
        .btn-toggle-act { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
        .btn-toggle-act:hover { background: #10b981; color: #000; }
        .btn-del { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
        .btn-del:hover { background: #ef4444; color: #fff; }
    </style>
</head>
<body>

<div class="container">
    <div class="header">
        <div>
            <h1>⚡ FSP LICENSE GENERATION & MONITOR</h1>
            <span style="font-size: 12px; color: #94a3b8;">Automated Hardware-Locked License Manager</span>
        </div>
        <div class="live-tag">
            <div class="live-dot"></div>
            <span>Real-time Sync Active</span>
        </div>
    </div>

    <div class="card">
        <h2>🔑 Issue New License Key</h2>
        <div class="gen-box">
            <select id="durationSelect">
                <option value="7">7 Days Validity (1 Week)</option>
                <option value="14">14 Days Validity (2 Weeks)</option>
                <option value="30" selected>30 Days Validity (1 Month)</option>
                <option value="60">60 Days Validity (2 Months)</option>
                <option value="365">365 Days Validity (1 Year)</option>
            </select>
            <button class="btn-primary" onclick="generateNewKey()">⚡ Generate Secure Key</button>
        </div>

        <div id="keyBox" class="key-result">
            <div>
                <span style="font-size: 11px; color: #94a3b8;">Generated License Key:</span><br>
                <span id="displayKey" class="key-text">---</span>
            </div>
            <button class="btn-sm btn-copy-sm" style="padding: 8px 14px;" onclick="copyKeyText(document.getElementById('displayKey').innerText)">📋 Copy Key</button>
        </div>
    </div>

    <div class="card">
        <h2>📋 Live Hardware Status & Control Deck</h2>
        <table>
            <thead>
                <tr>
                    <th>License Key</th>
                    <th>Plan</th>
                    <th>Status</th>
                    <th>Locked Hardware (HWID)</th>
                    <th>Time Remaining</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="keysTableBody">
                <tr><td colspan="6" style="text-align: center; color: #94a3b8;">Loading database records...</td></tr>
            </tbody>
        </table>
    </div>
</div>

<script>
    let currentKeysDataHash = "";

    async function loadKeys() {
        try {
            const res = await fetch('/api/admin/keys');
            const data = await res.json();
            
            const newHash = JSON.stringify(data.keys);
            if (newHash === currentKeysDataHash) {
                return;
            }
            currentKeysDataHash = newHash;

            const tbody = document.getElementById('keysTableBody');
            tbody.innerHTML = '';

            if (!data.keys || data.keys.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #94a3b8;">No license keys found.</td></tr>';
                return;
            }

            data.keys.forEach(k => {
                let badgeClass = 'badge-active';
                let statusLabel = 'ACTIVE';

                if (k.status === 'deactivated') {
                    badgeClass = 'badge-disabled';
                    statusLabel = 'DEACTIVATED';
                } else if (k.status === 'expired' || k.time_left === 'Expired') {
                    badgeClass = 'badge-expired';
                    statusLabel = 'EXPIRED';
                } else if (k.hwid === 'Unused') {
                    badgeClass = 'badge-pending';
                    statusLabel = 'UNUSED';
                }

                const isDeactivated = (k.status === 'deactivated');
                const toggleBtnText = isDeactivated ? 'Activate' : 'Deactivate';
                const toggleBtnClass = isDeactivated ? 'btn-toggle-act' : 'btn-toggle-deact';

                tbody.innerHTML += `
                    <tr>
                        <td class="key-mono">${k.key}</td>
                        <td>${k.duration}</td>
                        <td><span class="badge ${badgeClass}">${statusLabel}</span></td>
                        <td style="color: #94a3b8; font-family: monospace;">${k.hwid ? k.hwid.substring(0, 16) + '...' : 'Unbound'}</td>
                        <td style="color: ${k.time_left === 'Expired' ? '#ef4444' : '#00f2fe'}">${k.time_left}</td>
                        <td>
                            <div class="action-btns">
                                <button class="btn-sm btn-copy-sm" onclick="copyKeyText('${k.key}')">📋 Copy</button>
                                <button class="btn-sm ${toggleBtnClass}" onclick="toggleKeyStatus('${k.key}')">${toggleBtnText}</button>
                                <button class="btn-sm btn-del" onclick="deleteKey('${k.key}')">Delete</button>
                            </div>
                        </td>
                    </tr>
                `;
            });
        } catch (e) {
            console.error("Auto sync poll error:", e);
        }
    }

    async function generateNewKey() {
        const days = document.getElementById('durationSelect').value;
        const res = await fetch('/api/admin/generate', {
            method: 'POST',
            body: JSON.stringify({ days: days })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('displayKey').innerText = data.key;
            document.getElementById('keyBox').style.display = 'flex';
            currentKeysDataHash = "";
            loadKeys();
        }
    }

    async function toggleKeyStatus(key) {
        await fetch('/api/admin/toggle-status', {
            method: 'POST',
            body: JSON.stringify({ key: key })
        });
        currentKeysDataHash = "";
        loadKeys();
    }

    async function deleteKey(key) {
        if (!confirm(`Are you sure you want to completely remove key "${key}"?`)) return;
        await fetch('/api/admin/delete', {
            method: 'POST',
            body: JSON.stringify({ key: key })
        });
        currentKeysDataHash = "";
        loadKeys();
    }

    function copyKeyText(key) {
        navigator.clipboard.writeText(key);
        alert('Key copied: ' + key);
    }

    window.onload = () => {
        loadKeys();
        setInterval(loadKeys, 1500);
    };
</script>

</body>
</html>
"""

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def generate_secure_key(prefix="FSP"):
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    p3 = secrets.token_hex(2).upper()
    return f"{prefix}-{p1}-{p2}-{p3}"

@app.route("/", methods=["GET"])
@app.route("/admin", methods=["GET"])
def admin_page():
    return render_template_string(ADMIN_HTML)

@app.route("/api/admin/keys", methods=["GET"])
def get_all_keys():
    db = load_db()
    key_list = []
    now = datetime.utcnow()

    for key, data in db.items():
        time_left_str = "Awaiting First Activation"
        if data.get("first_used"):
            start_date = datetime.fromisoformat(data["first_used"])
            expiry_date = start_date + timedelta(days=data["duration_days"])
            remaining = expiry_date - now
            if remaining.total_seconds() <= 0:
                time_left_str = "Expired"
            else:
                days = remaining.days
                hours = int(remaining.seconds // 3600)
                time_left_str = f"{days}d {hours}h remaining"

        key_list.append({
            "key": key,
            "duration": f"{data.get('duration_days', 0)} Days",
            "status": data.get("status", "active"),
            "hwid": data.get("hwid") or "Unused",
            "time_left": time_left_str
        })
    return jsonify({"keys": list(reversed(key_list))})

@app.route("/api/admin/generate", methods=["POST"])
def generate_new_key():
    req = request.get_json(force=True)
    days = int(req.get("days", 30))

    db = load_db()
    new_key = generate_secure_key()
    while new_key in db:
        new_key = generate_secure_key()

    db[new_key] = {
        "duration_days": days,
        "first_used": None,
        "hwid": None,
        "status": "active"
    }
    save_db(db)
    return jsonify({"success": True, "key": new_key, "days": days})

@app.route("/api/admin/toggle-status", methods=["POST"])
def toggle_key_status():
    req = request.get_json(force=True)
    target_key = req.get("key", "").strip()
    db = load_db()

    if target_key in db:
        current_status = db[target_key].get("status", "active")
        new_status = "deactivated" if current_status == "active" else "active"
        db[target_key]["status"] = new_status
        save_db(db)
        return jsonify({"success": True, "new_status": new_status})
    return jsonify({"success": False, "message": "Key not found."}), 404

@app.route("/api/admin/delete", methods=["POST"])
def delete_key():
    req = request.get_json(force=True)
    target_key = req.get("key", "").strip()
    db = load_db()
    if target_key in db:
        del db[target_key]
        save_db(db)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Key not found."}), 404

@app.route("/api/verify-license", methods=["POST"])
def verify_license():
    req = request.get_json(force=True)
    key = req.get("key", "").strip()
    client_hwid = req.get("hwid", "UNKNOWN").strip().upper()

    db = load_db()
    # 1. Invalid / Galat Key Check
    if key not in db:
        return jsonify({
            "valid": False, 
            "message": f"Invalid Key! Key not found in system.\nPlease Contact Admin: {ADMIN_CONTACT_NUMBER}"
        }), 403

    record = db[key]
    
    # 2. Deactivated / Blocked Key Check
    if record.get("status") == "deactivated":
        return jsonify({
            "valid": False, 
            "message": f"This key has been deactivated by administrator.\nContact Admin: {ADMIN_CONTACT_NUMBER}"
        }), 403

    if record.get("status") != "active":
        return jsonify({
            "valid": False, 
            "message": f"Key is not active or has been revoked.\nContact Admin: {ADMIN_CONTACT_NUMBER}"
        }), 403

    now = datetime.utcnow()
    # First time activation: Machine HWID binding
    if not record.get("first_used"):
        record["first_used"] = now.isoformat()
        record["hwid"] = client_hwid
        save_db(db)

    # 3. Strict HWID Lock: Doosre PC par use hone se rokna
    saved_hwid = (record.get("hwid") or "").strip().upper()
    if saved_hwid and saved_hwid != client_hwid:
        return jsonify({
            "valid": False, 
            "message": f"Hardware Mismatch! This key is strictly locked to another PC.\nContact Admin: {ADMIN_CONTACT_NUMBER}"
        }), 403

    # 4. Expiry Check
    start_date = datetime.fromisoformat(record["first_used"])
    expiry_date = start_date + timedelta(days=record["duration_days"])
    remaining = expiry_date - now

    if remaining.total_seconds() <= 0:
        record["status"] = "expired"
        save_db(db)
        return jsonify({
            "valid": False, 
            "message": f"Your subscription has expired!\nPlease contact admin to renew: {ADMIN_CONTACT_NUMBER}"
        }), 403

    days_left = remaining.days
    hours_left = int(remaining.seconds // 3600)

    return jsonify({
        "valid": True,
        "message": f"Verification successful! Remaining: {days_left} Days {hours_left} Hours",
        "days_left": days_left
    }), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
