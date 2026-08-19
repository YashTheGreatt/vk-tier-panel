import os
import sqlite3
from flask import Flask, jsonify, redirect, render_template_string, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clan_data.db")

TIER_ORDER = {
    "HT1": 10, "LT1": 9,
    "HT2": 8,  "LT2": 7,
    "HT3": 6,  "LT3": 5,
    "HT4": 4,  "LT4": 3,
    "HT5": 2,  "LT5": 1,
    "OFFICIAL": 0
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            ign TEXT PRIMARY KEY,
            role_type TEXT,
            gamemode TEXT,
            tier TEXT,
            points INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return redirect("/leaderboard")

@app.route("/api/tiers")
def get_tiers():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT ign, role_type, gamemode, tier FROM members")
    rows = c.fetchall()
    conn.close()
    return jsonify({
        r[0]: {"type": r[1], "mode": r[2], "tier": r[3]} for r in rows
    })

@app.route("/leaderboard")
def leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT ign, role_type, gamemode, tier, points FROM members")
    all_members = c.fetchall()
    conn.close()

    cpvp = [m for m in all_members if m[2] == "CPvP"]
    sword = [m for m in all_members if m[2] == "Sword"]
    specialists = [m for m in all_members if m[1] == "Specialist"]

    cpvp.sort(key=lambda x: TIER_ORDER.get(str(x[3]).upper(), 0), reverse=True)
    sword.sort(key=lambda x: TIER_ORDER.get(str(x[3]).upper(), 0), reverse=True)
    specialists.sort(key=lambda x: x[4], reverse=True)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Void Knight Leaderboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #0c0d12; color: #fff; font-family: sans-serif; text-align: center; padding: 20px; }
            h1 { color: #9b59b6; letter-spacing: 2px; }
            .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
            .card { background: #161822; padding: 15px; border-radius: 10px; width: 320px; border: 1px solid #282b3d; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 10px; border-bottom: 1px solid #232736; text-align: left; }
            th { color: #a29bfe; font-size: 13px; }
            .tier { color: #ffd700; font-weight: bold; }
            .pts { color: #2ecc71; font-weight: bold; }
            .tag { color: #e74c3c; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>⚔️ VOID KNIGHT LEADERBOARDS ⚔️</h1>
        <div class="container">
            <div class="card">
                <h3>✦ CPvP Tierlist</h3>
                <table>
                    <tr><th>Rank</th><th>IGN</th><th>Tier</th></tr>
                    {% for p in cpvp %}
                    <tr>
                        <td>#{{ loop.index }}</td>
                        <td><span class="tag">VK</span> {{ p[0] }}</td>
                        <td class="tier">{{ p[3] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <div class="card">
                <h3>⚔️ Sword Tierlist</h3>
                <table>
                    <tr><th>Rank</th><th>IGN</th><th>Tier</th></tr>
                    {% for p in sword %}
                    <tr>
                        <td>#{{ loop.index }}</td>
                        <td><span class="tag">VK</span> {{ p[0] }}</td>
                        <td class="tier">{{ p[3] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            <div class="card">
                <h3>🛠️ Clan Specialists</h3>
                <table>
                    <tr><th>Rank</th><th>IGN</th><th>Role</th><th>Points</th></tr>
                    {% for s in specialists %}
                    <tr>
                        <td>#{{ loop.index }}</td>
                        <td><span class="tag">VK</span> {{ s[0] }}</td>
                        <td style="color:#00d2d3;">{{ s[2] }}</td>
                        <td class="pts">{{ s[4] }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, cpvp=cpvp, sword=sword, specialists=specialists)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")
        ign = request.form.get("ign", "").strip()

        if action == "add" and ign:
            mode = request.form.get("mode")
            role_type = "Specialist" if mode in ["Builder", "Grinder"] else "Combat"
            tier = request.form.get("tier", "").strip().upper() if role_type == "Combat" else "OFFICIAL"
            try:
                points = int(request.form.get("points", 0))
            except:
                points = 0

            c.execute("INSERT OR REPLACE INTO members (ign, role_type, gamemode, tier, points) VALUES (?, ?, ?, ?, ?)",
                      (ign, role_type, mode, tier, points))
            conn.commit()
            conn.close()
            return redirect("/admin")
            
        elif action == "delete" and ign:
            c.execute("DELETE FROM members WHERE ign = ?", (ign,))
            conn.commit()
            conn.close()
            return redirect("/admin")

    c.execute("SELECT ign, gamemode, tier, points FROM members")
    members = c.fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VK Admin Panel</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { background: #12131a; color: white; font-family: sans-serif; padding: 20px; display: flex; flex-direction: column; align-items: center; }
            .card { background: #1e212b; padding: 20px; border-radius: 8px; width: 90%; max-width: 500px; margin-bottom: 20px; }
            input, select, button { width: 100%; padding: 10px; margin: 8px 0; border-radius: 5px; border: none; box-sizing: border-box; }
            input, select { background: #2b2f3d; color: white; }
            button { background: #9b59b6; color: white; font-weight: bold; cursor: pointer; }
            .del-btn { background: #ed4245; padding: 5px 10px; width: auto; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            td, th { padding: 8px; border-bottom: 1px solid #333; text-align: left; }
        </style>
    </head>
    <body>
        <h2>🛡️ VOID KNIGHT ADMIN PANEL</h2>
        <div class="card">
            <h3>Add / Update Member</h3>
            <form method="POST">
                <input type="hidden" name="action" value="add">
                <input type="text" name="ign" placeholder="Minecraft IGN" required>
                <select name="mode" id="modeSelect" onchange="toggleInputs()">
                    <option value="CPvP">✦ Crystal PvP</option>
                    <option value="Sword">⚔️ Sword PvP</option>
                    <option value="Grinder">⛏️ Clan Grinder</option>
                    <option value="Builder">🏗️ Clan Builder</option>
                </select>
                <input type="text" name="tier" id="tierInput" placeholder="Tier (HT1, LT1, HT2, LT2...)" required>
                <input type="number" name="points" id="pointsInput" placeholder="Grind/Build Points" style="display:none;" value="0">
                <button type="submit">Save / Update Member</button>
            </form>
        </div>

        <script>
            function toggleInputs() {
                var mode = document.getElementById("modeSelect").value;
                var tierInput = document.getElementById("tierInput");
                var pointsInput = document.getElementById("pointsInput");
                if (mode === "Grinder" || mode === "Builder") {
                    tierInput.style.display = "none";
                    tierInput.required = false;
                    pointsInput.style.display = "block";
                } else {
                    tierInput.style.display = "block";
                    tierInput.required = true;
                    pointsInput.style.display = "none";
                }
            }
        </script>

        <div class="card" style="max-width: 650px;">
            <h3>Clan Roster</h3>
            <table>
                <tr><th>IGN</th><th>Role</th><th>Tier / Pts</th><th>Action</th></tr>
                {% for m in members %}
                <tr>
                    <td>{{ m[0] }}</td>
                    <td>{{ m[1] }}</td>
                    <td>{{ m[2] if m[1] in ['CPvP', 'Sword'] else (m[3]|string + ' pts') }}</td>
                    <td>
                        <form method="POST" style="margin:0;">
                            <input type="hidden" name="action" value="delete">
                            <input type="hidden" name="ign" value="{{ m[0] }}">
                            <button type="submit" class="del-btn">X</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """
    return render_template_string(html, members=members)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
