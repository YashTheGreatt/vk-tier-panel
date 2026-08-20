import os
import sqlite3
import hashlib
import secrets

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for
)

# ============================================================
# VOID KNIGHT - CONFIG
# ============================================================

app = Flask(__name__)

# Change this before making the source code public.
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "vk_" + hashlib.sha256(
        b"VoidKnight_Change_This_Secret_Key_2026"
    ).hexdigest()
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "clan_data.db")

# ============================================================
# ADMIN LOGIN
# ============================================================

ADMIN_USERNAME = "voidknight"
ADMIN_PASSWORD = "hyperdidiontopbabyy"

# ============================================================
# CLAN CONFIG
# ============================================================

CLAN_NAME = "VOID KNIGHT"
CLAN_TAG = "VK"

DISCORD_URL = "https://discord.gg/EV48TzhmeQ"

VALID_ROLES = {
    "CPvPer",
    "Sword",
    "Builder",
    "Grinder"
}

ROLE_INFO = {
    "CPvPer": {
        "icon": "✦",
        "label": "Crystal PvPer"
    },
    "Sword": {
        "icon": "⚔",
        "label": "Sword PvPer"
    },
    "Builder": {
        "icon": "◆",
        "label": "Builder"
    },
    "Grinder": {
        "icon": "⛏",
        "label": "Grinder"
    }
}


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            ign TEXT PRIMARY KEY COLLATE NOCASE,
            role TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# HELPERS
# ============================================================

def is_admin():
    return session.get("vk_admin") is True


def avatar_data(ign):
    """
    Generates a deterministic Minecraft-style SVG avatar.

    Same username = same avatar.
    Works for offline/cracked players too.
    No external skin API is required.
    """

    digest = hashlib.sha256(ign.lower().encode("utf-8")).hexdigest()

    palettes = [
        ("#8b5cf6", "#4c1d95"),
        ("#06b6d4", "#164e63"),
        ("#ef4444", "#7f1d1d"),
        ("#22c55e", "#14532d"),
        ("#f59e0b", "#78350f"),
        ("#ec4899", "#831843"),
        ("#3b82f6", "#172554"),
        ("#a855f7", "#3b0764"),
    ]

    index = int(digest[:2], 16) % len(palettes)
    bg1, bg2 = palettes[index]

    # Small deterministic pixel pattern.
    pixels = []
    for y in range(4):
        for x in range(4):
            n = int(digest[(y * 4 + x) % len(digest)], 16)

            if n % 2 == 0:
                px = 28 + x * 12
                py = 28 + y * 12

                pixels.append(
                    f'<rect x="{px}" y="{py}" '
                    f'width="12" height="12" fill="{bg2}"/>'
                )

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg"
         width="96"
         height="96"
         viewBox="0 0 96 96">

        <rect width="96" height="96" rx="14" fill="{bg1}"/>

        <rect x="20" y="16"
              width="56" height="64"
              rx="8"
              fill="#d7a67d"/>

        <rect x="20" y="16"
              width="56" height="18"
              rx="8"
              fill="{bg2}"/>

        <rect x="29" y="42"
              width="9" height="9"
              fill="#111827"/>

        <rect x="58" y="42"
              width="9" height="9"
              fill="#111827"/>

        <rect x="38" y="61"
              width="20" height="5"
              rx="2"
              fill="#7f1d1d"/>

        {''.join(pixels)}

    </svg>
    """

    return "data:image/svg+xml;base64," + (
        __import__("base64")
        .b64encode(svg.encode("utf-8"))
        .decode("utf-8")
    )


def get_members():
    conn = get_db()

    rows = conn.execute("""
        SELECT ign, role, points
        FROM members
        ORDER BY points DESC, ign COLLATE NOCASE ASC
    """).fetchall()

    conn.close()

    members = []

    for row in rows:
        role = row["role"]

        members.append({
            "ign": row["ign"],
            "role": role,
            "points": row["points"],
            "icon": ROLE_INFO.get(role, {}).get("icon", "✦"),
            "role_label": ROLE_INFO.get(role, {}).get("label", role),
            "avatar": avatar_data(row["ign"])
        })

    return members


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():
    return redirect("/leaderboard")


# ============================================================
# LIVE API FOR VOID KNIGHT MOD
# ============================================================

@app.route("/api/tiers")
def get_tiers():
    """
    Keeping this endpoint name means your existing mod URL
    can remain:

    https://voidknight.onrender.com/api/tiers

    Tier is no longer used.

    API response example:

    {
        "PlayerName": {
            "role": "CPvPer",
            "mode": "CPvPer",
            "type": "Combat",
            "points": 100
        }
    }
    """

    conn = get_db()

    rows = conn.execute("""
        SELECT ign, role, points
        FROM members
    """).fetchall()

    conn.close()

    data = {}

    for row in rows:
        role = row["role"]

        data[row["ign"]] = {
            "role": role,
            "mode": role,
            "type": (
                "Specialist"
                if role in ["Builder", "Grinder"]
                else "Combat"
            ),
            "points": row["points"]
        }

    response = jsonify(data)

    # Prevent old cached API responses.
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"

    return response


# ============================================================
# LEADERBOARD
# ============================================================

@app.route("/leaderboard")
def leaderboard():

    members = get_members()

    cpvp_members = [
        m for m in members
        if m["role"] == "CPvPer"
    ]

    sword_members = [
        m for m in members
        if m["role"] == "Sword"
    ]

    specialists = [
        m for m in members
        if m["role"] in ["Builder", "Grinder"]
    ]

    html = r"""
<!DOCTYPE html>
<html lang="en">
<head>

<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Void Knight Rankings</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;
    background:
        radial-gradient(
            circle at top,
            #182235 0%,
            #0c111a 45%,
            #080b11 100%
        );
    color: #e8edf7;
    font-family:
        Arial,
        Helvetica,
        sans-serif;
}

/* ================= NAVBAR ================= */

.navbar {
    width: min(1200px, 94%);
    margin: 22px auto;
    padding: 14px 20px;

    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;

    background: rgba(20, 29, 43, 0.92);

    border: 1px solid #26344a;
    border-radius: 16px;

    box-shadow:
        0 12px 35px rgba(0,0,0,.25);
}

.brand {
    display: flex;
    align-items: center;
    gap: 11px;

    text-decoration: none;
    color: white;

    font-weight: 900;
    font-size: 20px;
    letter-spacing: 1px;
}

.vk-logo {
    width: 44px;
    height: 44px;

    display: grid;
    place-items: center;

    border-radius: 11px;

    background:
        linear-gradient(
            135deg,
            #8b5cf6,
            #4338ca
        );

    color: white;

    font-weight: 900;
    box-shadow:
        0 0 25px rgba(139,92,246,.35);
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 10px;
}

.nav-links a {
    text-decoration: none;
    color: #aeb9ca;

    padding: 10px 14px;
    border-radius: 10px;

    font-weight: bold;
}

.nav-links a:hover {
    color: white;
    background: #202c3e;
}

.discord {
    color: #d9ddff !important;
}

/* ================= MAIN ================= */

.main {
    width: min(1200px, 94%);
    margin: 35px auto 60px;
}

.hero {
    text-align: center;
    margin-bottom: 32px;
}

.hero h1 {
    margin: 0;
    font-size: clamp(30px, 6vw, 52px);
    letter-spacing: 2px;

    background:
        linear-gradient(
            90deg,
            #a78bfa,
            #60a5fa,
            #c084fc
        );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero p {
    color: #8e9bb0;
    margin-top: 10px;
}

/* ================= STATS ================= */

.stats {
    display: grid;

    grid-template-columns:
        repeat(auto-fit, minmax(180px, 1fr));

    gap: 14px;
    margin-bottom: 28px;
}

.stat {
    background: rgba(20,29,43,.85);

    border: 1px solid #26344a;
    border-radius: 14px;

    padding: 18px;
}

.stat-number {
    font-size: 28px;
    font-weight: 900;
    color: #a78bfa;
}

.stat-label {
    color: #8390a5;
    margin-top: 5px;
}

/* ================= LEADERBOARD ================= */

.section {
    margin-top: 28px;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 10px;

    font-size: 20px;
    font-weight: 800;

    margin-bottom: 12px;
}

.board {
    display: grid;
    gap: 10px;
}

.player {
    display: grid;

    grid-template-columns:
        70px 64px 1fr auto;

    align-items: center;

    gap: 15px;

    padding: 12px 18px;

    background:
        linear-gradient(
            90deg,
            rgba(27,38,55,.95),
            rgba(17,25,37,.95)
        );

    border: 1px solid #26344a;
    border-radius: 15px;

    transition:
        transform .15s,
        border-color .15s;
}

.player:hover {
    transform: translateY(-2px);
    border-color: #7055c8;
}

.rank {
    font-size: 27px;
    font-weight: 900;
    color: #cbd5e1;
}

.avatar {
    width: 54px;
    height: 54px;

    border-radius: 12px;

    object-fit: cover;

    background: #111827;

    border: 1px solid #334155;
}

.player-info {
    min-width: 0;
}

.name {
    font-size: 19px;
    font-weight: 800;

    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.role-line {
    margin-top: 6px;

    display: flex;
    align-items: center;
    gap: 8px;

    color: #98a6b9;
    font-size: 14px;
}

.role-icon {
    width: 25px;
    height: 25px;

    display: grid;
    place-items: center;

    background: #151e2c;

    border: 1px solid #334155;
    border-radius: 8px;

    color: #a78bfa;
}

.points {
    min-width: 90px;

    text-align: right;

    color: #fbbf24;
    font-weight: 800;
}

.points small {
    display: block;
    margin-top: 3px;

    color: #64748b;
    font-size: 11px;
}

.empty {
    padding: 30px;

    text-align: center;
    color: #778399;

    background: #131c29;

    border: 1px solid #26344a;
    border-radius: 14px;
}

/* ================= FOOTER ================= */

footer {
    text-align: center;
    color: #667085;

    padding: 35px 15px;
}

footer strong {
    color: #9f7aea;
}

/* ================= MOBILE ================= */

@media (max-width: 650px) {

    .navbar {
        padding: 12px;
    }

    .nav-links a:not(.discord) {
        display: none;
    }

    .brand {
        font-size: 16px;
    }

    .player {
        grid-template-columns:
            42px 50px 1fr;

        gap: 10px;
        padding: 11px;
    }

    .rank {
        font-size: 20px;
    }

    .avatar {
        width: 46px;
        height: 46px;
    }

    .points {
        display: none;
    }

}

</style>

</head>

<body>

<nav class="navbar">

    <a href="/leaderboard" class="brand">

        <div class="vk-logo">VK</div>

        <span>VOID KNIGHT</span>

    </a>

    <div class="nav-links">

        <a href="/leaderboard">
            🏆 Rankings
        </a>

        <a class="discord"
           href="{{ discord_url }}"
           target="_blank"
           rel="noopener">
            Discord ↗
        </a>

        <a href="/admin">
            Admin
        </a>

    </div>

</nav>


<main class="main">

    <div class="hero">

        <h1>VOID KNIGHT RANKINGS</h1>

        <p>
            Official Void Knight team members and specialists
        </p>

    </div>


    <div class="stats">

        <div class="stat">

            <div class="stat-number">
                {{ members|length }}
            </div>

            <div class="stat-label">
                Total Members
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {{ cpvp|length }}
            </div>

            <div class="stat-label">
                Crystal PvPers
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {{ sword|length }}
            </div>

            <div class="stat-label">
                Sword PvPers
            </div>

        </div>


        <div class="stat">

            <div class="stat-number">
                {{ specialists|length }}
            </div>

            <div class="stat-label">
                Specialists
            </div>

        </div>

    </div>


    <section class="section">

        <div class="section-title">
            ✦ Crystal PvP
        </div>

        <div class="board">

        {% if cpvp %}

            {% for player in cpvp %}

            <div class="player">

                <div class="rank">
                    #{{ loop.index }}
                </div>

                <img
                    class="avatar"
                    src="{{ player.avatar }}"
                    alt="{{ player.ign }}"
                >

                <div class="player-info">

                    <div class="name">
                        {{ player.ign }}
                    </div>

                    <div class="role-line">

                        <div class="role-icon">
                            {{ player.icon }}
                        </div>

                        {{ player.role_label }}

                    </div>

                </div>

                <div class="points">

                    {{ player.points }}

                    <small>POINTS</small>

                </div>

            </div>

            {% endfor %}

        {% else %}

            <div class="empty">
                No Crystal PvP members yet.
            </div>

        {% endif %}

        </div>

    </section>


    <section class="section">

        <div class="section-title">
            ⚔ Sword PvP
        </div>

        <div class="board">

        {% if sword %}

            {% for player in sword %}

            <div class="player">

                <div class="rank">
                    #{{ loop.index }}
                </div>

                <img
                    class="avatar"
                    src="{{ player.avatar }}"
                    alt="{{ player.ign }}"
                >

                <div class="player-info">

                    <div class="name">
                        {{ player.ign }}
                    </div>

                    <div class="role-line">

                        <div class="role-icon">
                            {{ player.icon }}
                        </div>

                        {{ player.role_label }}

                    </div>

                </div>

                <div class="points">

                    {{ player.points }}

                    <small>POINTS</small>

                </div>

            </div>

            {% endfor %}

        {% else %}

            <div class="empty">
                No Sword PvP members yet.
            </div>

        {% endif %}

        </div>

    </section>


    <section class="section">

        <div class="section-title">
            🛠 Clan Specialists
        </div>

        <div class="board">

        {% if specialists %}

            {% for player in specialists %}

            <div class="player">

                <div class="rank">
                    #{{ loop.index }}
                </div>

                <img
                    class="avatar"
                    src="{{ player.avatar }}"
                    alt="{{ player.ign }}"
                >

                <div class="player-info">

                    <div class="name">
                        {{ player.ign }}
                    </div>

                    <div class="role-line">

                        <div class="role-icon">
                            {{ player.icon }}
                        </div>

                        {{ player.role_label }}

                    </div>

                </div>

                <div class="points">

                    {{ player.points }}

                    <small>POINTS</small>

                </div>

            </div>

            {% endfor %}

        {% else %}

            <div class="empty">
                No specialists added yet.
            </div>

        {% endif %}

        </div>

    </section>

</main>


<footer>

    <strong>VOID KNIGHT</strong>
    &nbsp;•&nbsp;
    Official Clan Rankings

</footer>

</body>
</html>
"""

    return render_template_string(
        html,
        members=members,
        cpvp=cpvp_members,
        sword=sword_members,
        specialists=specialists,
        discord_url=DISCORD_URL
    )


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if is_admin():
        return redirect("/admin")

    error = None

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if (
            secrets.compare_digest(
                username,
                ADMIN_USERNAME
            )
            and
            secrets.compare_digest(
                password,
                ADMIN_PASSWORD
            )
        ):
            session.clear()
            session["vk_admin"] = True

            return redirect("/admin")

        error = "Invalid username or password."

    return render_template_string(r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>VK Admin Login</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100vh;

    display: grid;
    place-items: center;

    padding: 20px;

    background:
        radial-gradient(
            circle at top,
            #1d2840,
            #090d14 65%
        );

    font-family: Arial, sans-serif;
    color: white;
}

.card {
    width: 100%;
    max-width: 400px;

    padding: 30px;

    background: #121a27;

    border: 1px solid #2a3950;
    border-radius: 20px;

    box-shadow:
        0 20px 60px rgba(0,0,0,.4);
}

.logo {
    width: 65px;
    height: 65px;

    margin: 0 auto 18px;

    display: grid;
    place-items: center;

    border-radius: 18px;

    background:
        linear-gradient(
            135deg,
            #8b5cf6,
            #4338ca
        );

    font-size: 22px;
    font-weight: 900;
}

h1 {
    text-align: center;
    margin: 0;
}

p {
    text-align: center;
    color: #8997aa;
}

input,
button {
    width: 100%;

    padding: 13px;

    margin-top: 12px;

    border-radius: 10px;

    box-sizing: border-box;
}

input {
    background: #0b111b;
    color: white;

    border: 1px solid #2c3b52;
}

button {
    border: 0;

    background:
        linear-gradient(
            135deg,
            #8b5cf6,
            #6366f1
        );

    color: white;

    font-weight: 800;
    cursor: pointer;
}

.error {
    margin-top: 15px;

    padding: 10px;

    background: #4a1d27;

    color: #fda4af;

    border-radius: 8px;

    text-align: center;
}

.back {
    display: block;

    margin-top: 18px;

    text-align: center;

    color: #9f7aea;

    text-decoration: none;
}

</style>

</head>

<body>

<div class="card">

    <div class="logo">
        VK
    </div>

    <h1>Admin Login</h1>

    <p>
        Void Knight Administration
    </p>

    <form method="POST">

        <input
            name="username"
            placeholder="Username"
            autocomplete="username"
            required
        >

        <input
            type="password"
            name="password"
            placeholder="Password"
            autocomplete="current-password"
            required
        >

        <button type="submit">
            Login
        </button>

    </form>

    {% if error %}

        <div class="error">
            {{ error }}
        </div>

    {% endif %}

    <a class="back"
       href="/leaderboard">
        ← Back to Rankings
    </a>

</div>

</body>
</html>
""", error=error)


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect("/admin/login")


# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin", methods=["GET", "POST"])
def admin():

    if not is_admin():
        return redirect("/admin/login")

    conn = get_db()

    if request.method == "POST":

        action = request.form.get(
            "action",
            ""
        )

        # ----------------------------------------------------
        # ADD / UPDATE
        # ----------------------------------------------------

        if action == "save":

            ign = request.form.get(
                "ign",
                ""
            ).strip()

            role = request.form.get(
                "role",
                ""
            ).strip()

            try:
                points = int(
                    request.form.get(
                        "points",
                        0
                    )
                )
            except (TypeError, ValueError):
                points = 0

            points = max(0, points)

            if ign and role in VALID_ROLES:

                conn.execute("""
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

        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        elif action == "delete":

            ign = request.form.get(
                "ign",
                ""
            ).strip()

            if ign:

                conn.execute(
                    "DELETE FROM members WHERE ign = ?",
                    (ign,)
                )

                conn.commit()

        conn.close()

        return redirect("/admin")

    rows = conn.execute("""
        SELECT ign, role, points
        FROM members
        ORDER BY points DESC, ign COLLATE NOCASE ASC
    """).fetchall()

    conn.close()

    return render_template_string(r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>VK Admin Panel</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;

    background: #0b1018;

    color: white;

    font-family: Arial, sans-serif;
}

nav {
    width: min(1100px, 94%);

    margin: 20px auto;

    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 10px;
}

.logo {
    font-size: 20px;
    font-weight: 900;

    color: #a78bfa;
}

nav a {
    color: #b6c2d2;

    text-decoration: none;

    margin-left: 12px;
}

.container {
    width: min(1100px, 94%);
    margin: 30px auto;
}

h1 {
    margin-bottom: 25px;
}

.grid {
    display: grid;

    grid-template-columns:
        minmax(280px, 390px) 1fr;

    gap: 20px;
}

.card {
    background: #121b28;

    border: 1px solid #29394f;

    border-radius: 16px;

    padding: 20px;
}

input,
select,
button {
    width: 100%;

    padding: 12px;

    margin-top: 10px;

    border-radius: 9px;

    box-sizing: border-box;
}

input,
select {
    background: #0a1019;

    border: 1px solid #2a3a51;

    color: white;
}

button {
    border: 0;

    background: #7958db;

    color: white;

    font-weight: 800;

    cursor: pointer;
}

table {
    width: 100%;

    border-collapse: collapse;

    margin-top: 10px;
}

th,
td {
    padding: 12px 8px;

    border-bottom: 1px solid #243247;

    text-align: left;
}

th {
    color: #8391a5;
    font-size: 12px;
}

.role {
    color: #a78bfa;
    font-weight: bold;
}

.points {
    color: #fbbf24;
}

.delete {
    width: auto;

    margin: 0;

    padding: 8px 12px;

    background: #b91c1c;
}

.edit-note {
    color: #718096;
    font-size: 13px;
}

@media(max-width: 800px) {

    .grid {
        grid-template-columns: 1fr;
    }

    table {
        font-size: 13px;
    }

}

</style>

</head>

<body>

<nav>

    <div class="logo">
        🛡 VOID KNIGHT ADMIN
    </div>

    <div>

        <a href="/leaderboard">
            Leaderboard
        </a>

        <a href="/admin/logout">
            Logout
        </a>

    </div>

</nav>


<div class="container">

    <h1>
        Clan Management
    </h1>

    <div class="grid">


        <!-- ADD MEMBER -->

        <div class="card">

            <h2>
                Add / Update Member
            </h2>

            <p class="edit-note">
                Using the same Minecraft IGN updates the existing member.
            </p>

            <form method="POST">

                <input
                    type="hidden"
                    name="action"
                    value="save"
                >

                <input
                    name="ign"
                    placeholder="Minecraft Username"
                    maxlength="32"
                    required
                >

                <select
                    name="role"
                    required
                >

                    <option value="CPvPer">
                        ✦ CPvPer
                    </option>

                    <option value="Sword">
                        ⚔ Sword
                    </option>

                    <option value="Builder">
                        ◆ Builder
                    </option>

                    <option value="Grinder">
                        ⛏ Grinder
                    </option>

                </select>

                <input
                    type="number"
                    name="points"
                    placeholder="Points"
                    value="0"
                    min="0"
                    required
                >

                <button type="submit">
                    Save Member
                </button>

            </form>

        </div>


        <!-- ROSTER -->

        <div class="card">

            <h2>
                Current Roster
            </h2>

            <p class="edit-note">
                {{ members|length }} total member(s)
            </p>

            <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        Username
                    </th>

                    <th>
                        Role
                    </th>

                    <th>
                        Points
                    </th>

                    <th>
                        Action
                    </th>

                </tr>


                {% for member in members %}

                <tr>

                    <td>
                        {{ member["ign"] }}
                    </td>

                    <td class="role">
                        {{ member["role"] }}
                    </td>

                    <td class="points">
                        {{ member["points"] }}
                    </td>

                    <td>

                        <form
                            method="POST"
                            onsubmit="
                                return confirm(
                                    'Delete {{ member["ign"] }}?'
                                );
                            "
                        >

                            <input
                                type="hidden"
                                name="action"
                                value="delete"
                            >

                            <input
                                type="hidden"
                                name="ign"
                                value="{{ member["ign"] }}"
                            >

                            <button
                                type="submit"
                                class="delete"
                            >
                                Delete
                            </button>

                        </form>

                    </td>

                </tr>

                {% else %}

                <tr>

                    <td
                        colspan="4"
                        style="
                            text-align:center;
                            color:#718096;
                            padding:30px;
                        "
                    >
                        No members yet.
                    </td>

                </tr>

                {% endfor %}

            </table>

            </div>

        </div>

    </div>

</div>

</body>
</html>
""", members=rows)


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
