import os
import sqlite3

from flask import Flask, jsonify, redirect, render_template_string, request

app = Flask(__name__)

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "clan_data.db"
)

VALID_ROLES = ["CPVPER", "SWORD", "BUILDER", "GRINDER"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            ign TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            points INTEGER DEFAULT 0
        )
    """)

    # Old database migration:
    # If your existing database has gamemode but no role,
    # copy gamemode values into role.
    columns = [
        row[1]
        for row in c.execute("PRAGMA table_info(members)").fetchall()
    ]

    if "role" not in columns:
        c.execute("ALTER TABLE members ADD COLUMN role TEXT")

        if "gamemode" in columns:
            c.execute("""
                UPDATE members
                SET role = gamemode
                WHERE role IS NULL
            """)

    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    return redirect("/leaderboard")


# ============================================================
# API FOR THE VOIDKNIGHT MINECRAFT MOD
# ============================================================

@app.route("/api/tiers")
def get_members():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT ign, role, points
        FROM members
    """)

    rows = c.fetchall()
    conn.close()

    data = {}

    for ign, role, points in rows:
        role = (role or "").upper().strip()

        data[ign] = {
            # Current mod compatibility
            "mode": role,

            # New cleaner field
            "role": role,

            # Kept for future points/leaderboard features
            "points": points or 0
        }

    return jsonify(data)


# ============================================================
# LEADERBOARD
# ============================================================

@app.route("/leaderboard")
def leaderboard():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT ign, role, points
        FROM members
        ORDER BY points DESC, ign COLLATE NOCASE ASC
    """)

    members = c.fetchall()
    conn.close()

    roles = {
        "CPVPER": [],
        "SWORD": [],
        "BUILDER": [],
        "GRINDER": []
    }

    for member in members:
        ign, role, points = member
        role = (role or "").upper().strip()

        if role in roles:
            roles[role].append(member)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>VoidKnight</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                background: #0c0d12;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
                margin: 0;
            }

            h1 {
                color: #9b59b6;
                letter-spacing: 2px;
            }

            .subtitle {
                color: #a0a0a0;
                margin-bottom: 25px;
            }

            .container {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 20px;
                max-width: 1100px;
                margin: auto;
            }

            .card {
                background: #161822;
                padding: 18px;
                border-radius: 12px;
                width: 300px;
                border: 1px solid #282b3d;
            }

            .role {
                color: #a29bfe;
                letter-spacing: 1px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }

            th, td {
                padding: 10px;
                border-bottom: 1px solid #232736;
                text-align: left;
            }

            th {
                color: #a29bfe;
                font-size: 13px;
            }

            .vk {
                color: #9b59b6;
                font-weight: bold;
            }

            .pts {
                color: #2ecc71;
                font-weight: bold;
            }

            .empty {
                color: #777;
                padding: 15px;
            }
        </style>
    </head>

    <body>

        <h1>⚔ VOIDKNIGHT ⚔</h1>

        <div class="subtitle">
            Official Team Roster
        </div>

        <div class="container">

            {% for role_name, players in roles.items() %}

            <div class="card">

                <h3 class="role">
                    {{ role_name }}
                </h3>

                {% if players %}

                <table>
                    <tr>
                        <th>#</th>
                        <th>IGN</th>
                        <th>Points</th>
                    </tr>

                    {% for p in players %}
                    <tr>
                        <td>{{ loop.index }}</td>

                        <td>
                            <span class="vk">VK</span>
                            {{ p[0] }}
                        </td>

                        <td class="pts">
                            {{ p[2] }}
                        </td>
                    </tr>
                    {% endfor %}

                </table>

                {% else %}

                <div class="empty">
                    No members yet
                </div>

                {% endif %}

            </div>

            {% endfor %}

        </div>

    </body>
    </html>
    """

    return render_template_string(
        html,
        roles=roles
    )


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action")

        ign = request.form.get(
            "ign",
            ""
        ).strip()

        # ----------------------------------------------------
        # ADD / UPDATE MEMBER
        # ----------------------------------------------------

        if action == "save" and ign:
            role = request.form.get(
                "role",
                ""
            ).upper().strip()

            if role not in VALID_ROLES:
                conn.close()
                return redirect("/admin")

            try:
                points = int(
                    request.form.get(
                        "points",
                        0
                    )
                )
            except (TypeError, ValueError):
                points = 0

            c.execute("""
                INSERT INTO members (
                    ign,
                    role,
                    points
                )
                VALUES (?, ?, ?)

                ON CONFLICT(ign)
                DO UPDATE SET
                    role = excluded.role,
                    points = excluded.points
            """, (
                ign,
                role,
                points
            ))

            conn.commit()
            conn.close()

            return redirect("/admin")

        # ----------------------------------------------------
        # DELETE MEMBER
        # ----------------------------------------------------

        elif action == "delete" and ign:

            c.execute(
                "DELETE FROM members WHERE ign = ?",
                (ign,)
            )

            conn.commit()
            conn.close()

            return redirect("/admin")

    # Get all members

    c.execute("""
        SELECT ign, role, points
        FROM members
        ORDER BY ign COLLATE NOCASE ASC
    """)

    members = c.fetchall()
    conn.close()

    html = """
    <!DOCTYPE html>
    <html>
    <head>

        <title>VoidKnight Admin</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <style>

            * {
                box-sizing: border-box;
            }

            body {
                background: #12131a;
                color: white;
                font-family: Arial, sans-serif;
                padding: 20px;
                margin: 0;

                display: flex;
                flex-direction: column;
                align-items: center;
            }

            .card {
                background: #1e212b;
                padding: 20px;
                border-radius: 10px;
                width: 95%;
                max-width: 700px;
                margin-bottom: 20px;
            }

            input,
            select,
            button {
                width: 100%;
                padding: 11px;
                margin: 8px 0;
                border-radius: 6px;
                border: none;
                box-sizing: border-box;
            }

            input,
            select {
                background: #2b2f3d;
                color: white;
            }

            button {
                background: #9b59b6;
                color: white;
                font-weight: bold;
                cursor: pointer;
            }

            .del-btn {
                background: #ed4245;
                padding: 7px 12px;
                width: auto;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }

            td,
            th {
                padding: 9px;
                border-bottom: 1px solid #333;
                text-align: left;
            }

            th {
                color: #a29bfe;
            }

            .role {
                color: #00d2d3;
                font-weight: bold;
            }

            .points {
                color: #2ecc71;
            }

        </style>

    </head>

    <body>

        <h2>🛡 VOIDKNIGHT ADMIN PANEL</h2>

        <div class="card">

            <h3>Add / Update Team Member</h3>

            <form method="POST">

                <input
                    type="hidden"
                    name="action"
                    value="save"
                >

                <input
                    type="text"
                    name="ign"
                    placeholder="Minecraft IGN"
                    required
                >

                <select
                    name="role"
                    required
                >
                    <option value="CPVPER">
                        ⚔ CPVPER
                    </option>

                    <option value="SWORD">
                        🗡 SWORD
                    </option>

                    <option value="BUILDER">
                        🧱 BUILDER
                    </option>

                    <option value="GRINDER">
                        ⛏ GRINDER
                    </option>
                </select>

                <input
                    type="number"
                    name="points"
                    placeholder="Points (for future leaderboard)"
                    value="0"
                    min="0"
                >

                <button type="submit">
                    Save / Update Member
                </button>

            </form>

        </div>


        <div class="card">

            <h3>Current Team</h3>

            <table>

                <tr>
                    <th>IGN</th>
                    <th>Role</th>
                    <th>Points</th>
                    <th>Action</th>
                </tr>

                {% for m in members %}

                <tr>

                    <td>{{ m[0] }}</td>

                    <td class="role">
                        {{ m[1] }}
                    </td>

                    <td class="points">
                        {{ m[2] }}
                    </td>

                    <td>

                        <form
                            method="POST"
                            style="margin:0;"
                        >

                            <input
                                type="hidden"
                                name="action"
                                value="delete"
                            >

                            <input
                                type="hidden"
                                name="ign"
                                value="{{ m[0] }}"
                            >

                            <button
                                type="submit"
                                class="del-btn"
                            >
                                Delete
                            </button>

                        </form>

                    </td>

                </tr>

                {% endfor %}

            </table>

        </div>

    </body>
    </html>
    """

    return render_template_string(
        html,
        members=members
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
