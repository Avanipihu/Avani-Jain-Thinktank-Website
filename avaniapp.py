import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, session

# Force stdout to flush immediately so print() shows in Render logs right away
sys.stdout.reconfigure(line_buffering=True)

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
app.secret_key = os.environ.get("SECRET_KEY", "avania_super_secret_key")

DATABASE_URL = os.environ.get('DATABASE_URL')

# ── Render gives postgres:// but psycopg2 needs postgresql:// ──
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def initialize_database():
    """Creates tables only if they don't exist yet. Never drops data."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(120) NOT NULL,
            username VARCHAR(60) UNIQUE NOT NULL,
            password TEXT NOT NULL,
            expert_points INTEGER DEFAULT 0,
            first_name VARCHAR(60),
            last_name VARCHAR(60)
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            problem TEXT,
            users TEXT,
            solution TEXT,
            advantage TEXT,
            impact TEXT,
            category VARCHAR(100),
            status VARCHAR(20) DEFAULT 'Private',
            owner VARCHAR(60) NOT NULL,
            version VARCHAR(20) DEFAULT '1.0'
        );
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            idea_title VARCHAR(255) NOT NULL,
            innovation VARCHAR(5),
            feasibility VARCHAR(5),
            usefulness VARCHAR(5),
            clarity VARCHAR(5),
            notes TEXT,
            reviewer VARCHAR(60) NOT NULL
        );
    ''')

    conn.commit()
    cur.close()
    conn.close()

if DATABASE_URL:
    try:
        initialize_database()
        print("Database tables ready.", flush=True)
    except Exception as e:
        print(f"DB init warning: {e}", flush=True)

# ── ROUTES ──

@app.route("/")
def home():
    return render_template("avanihome.html")

@app.route("/about")
def about():
    return render_template("avaniabout.html")

@app.route("/exit")
def exit_app():
    session.clear()
    return render_template("avaniexit.html")

@app.route("/login")
def login():
    status       = request.args.get('status')
    submitted    = request.args.get('submitted')
    current_user = session.get('username')

    all_ideas   = []
    all_reviews = []

    if DATABASE_URL:
        try:
            conn = get_db_connection()
            cur  = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute('''
                SELECT title AS "Title", problem AS "Problem", users AS "Users",
                       solution AS "Solution", advantage AS "Advantage", impact AS "Impact",
                       category AS "Category", status AS "Status", owner AS "Owner",
                       version AS "Version"
                FROM ideas
                WHERE status = 'Public' OR owner = %s
            ''', (current_user,))
            all_ideas = [dict(r) for r in cur.fetchall()]

            cur.execute('''
                SELECT idea_title AS "IdeaTitle", innovation AS "Innovation",
                       feasibility AS "Feasibility", usefulness AS "Usefulness",
                       clarity AS "Clarity", notes AS "Notes", reviewer AS "Reviewer"
                FROM reviews
            ''')
            all_reviews = [dict(r) for r in cur.fetchall()]

            cur.close()
            conn.close()
        except Exception as e:
            print(f"DB read error: {e}", flush=True)

    return render_template("avanilogin.html",
                           status=status,
                           submitted=submitted,
                           ideas=all_ideas,
                           reviews=all_reviews,
                           current_user=current_user)

@app.route("/register", methods=["POST"])
def register():
    first_name = request.form.get("first_name", "").strip()
    last_name  = request.form.get("last_name",  "").strip()
    username   = request.form.get("username",   "").strip()
    contact    = request.form.get("contact",    "").strip()
    password   = request.form.get("password",   "").strip()

    print(f"REGISTER attempt: username='{username}' contact='{contact}' "
          f"password_len={len(password)} first='{first_name}' last='{last_name}'", flush=True)

    if not username or not contact or not password:
        print("REGISTER blocked: a required field was empty.", flush=True)
        return redirect(url_for('login') + "?status=reg_error")

    try:
        conn = get_db_connection()
        cur  = conn.cursor()

        cur.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(%s);", (username,))
        if cur.fetchone():
            cur.close()
            conn.close()
            print(f"REGISTER blocked: username '{username}' already taken.", flush=True)
            return redirect(url_for('login') + "?status=username_taken")

        cur.execute('''
            INSERT INTO users (email, username, password, expert_points, first_name, last_name)
            VALUES (%s, %s, %s, 0, %s, %s);
        ''', (contact, username, password, first_name, last_name))

        conn.commit()
        cur.close()
        conn.close()
        print(f"REGISTER success: '{username}' created.", flush=True)
    except Exception as e:
        print(f"REGISTER DB ERROR: {repr(e)}", flush=True)
        return redirect(url_for('login') + "?status=reg_error")

    return redirect(url_for('login'))

@app.route("/login_check", methods=["POST"])
def login_check():
    u = request.form.get("username", "").strip()
    p = request.form.get("password", "").strip()

    try:
        conn = get_db_connection()
        cur  = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
            SELECT username FROM users
            WHERE (username = %s OR email = %s) AND password = %s;
        ''', (u, u, p))
        user = cur.fetchone()

        cur.close()
        conn.close()

        if user:
            session['username'] = user['username']
            return redirect(url_for('login', status='success'))

    except Exception as e:
        print(f"LOGIN DB ERROR: {repr(e)}", flush=True)

    return redirect(url_for('login', status='failed'))

@app.route("/share_idea", methods=["POST"])
def share_idea():
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute('''
            INSERT INTO ideas (title, problem, users, solution, advantage, impact,
                               category, status, owner, version)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        ''', (
            request.form.get("title",     "").strip(),
            request.form.get("problem",   "").strip(),
            request.form.get("users",     "").strip(),
            request.form.get("solution",  "").strip(),
            request.form.get("advantage", "").strip(),
            request.form.get("impact",    "").strip(),
            request.form.get("category",  "").strip(),
            request.form.get("status",    "Private"),
            session.get('username', 'Guest'),
            "1.0"
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"SHARE IDEA DB ERROR: {repr(e)}", flush=True)

    return redirect(url_for('login', status='success', submitted='idea'))

@app.route("/submit_review", methods=["POST"])
def submit_review():
    try:
        conn = get_db_connection()
        cur  = conn.cursor()
        cur.execute('''
            INSERT INTO reviews (idea_title, innovation, feasibility,
                                 usefulness, clarity, notes, reviewer)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        ''', (
            request.form.get("idea_title",  "").strip(),
            request.form.get("innovation",  "3"),
            request.form.get("feasibility", "3"),
            request.form.get("usefulness",  "3"),
            request.form.get("clarity",     "3"),
            request.form.get("notes",        "").strip(),
            session.get('username', 'Guest')
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"SUBMIT REVIEW DB ERROR: {repr(e)}", flush=True)

    if request.headers.get('X-Requested-With') == 'fetch':
        return '', 200
    return redirect(url_for('login', status='success', submitted='review'))

@app.route("/export_pdf/<title>")
def export_pdf(title):
    return f"Generating PDF for {title}... (Feature coming soon)", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
