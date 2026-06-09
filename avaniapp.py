import os
import csv
from flask import Flask, render_template, request, redirect, url_for, session

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__,
            template_folder=os.path.join(base_dir, 'templates'),
            static_folder=os.path.join(base_dir, 'static'))
app.secret_key = "avania_super_secret_key"

def initialize_files():
    files_headers = {
        "users.csv":   ["Email", "Username", "Password", "ExpertPoints", "FirstName", "LastName"],
        "ideas.csv":   ["Title", "Problem", "Users", "Solution", "Advantage", "Impact",
                        "Category", "Status", "Owner", "Version"],
        "reviews.csv": ["IdeaTitle", "Innovation", "Feasibility", "Usefulness",
                        "Clarity", "Notes", "Reviewer"]
    }
    for filename, headers in files_headers.items():
        if not os.path.exists(filename):
            with open(filename, "w", newline="") as f:
                csv.writer(f).writerow(headers)

initialize_files()

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
    status    = request.args.get('status')
    submitted = request.args.get('submitted')
    current_user = session.get('username')

    all_ideas = []
    if os.path.exists("ideas.csv"):
        with open("ideas.csv", "r") as f:
            for row in csv.DictReader(f):
                if row.get("Status") == "Public" or row.get("Owner") == current_user:
                    all_ideas.append(row)

    all_reviews = []
    if os.path.exists("reviews.csv"):
        with open("reviews.csv", "r") as f:
            all_reviews = list(csv.DictReader(f))

    return render_template("avanilogin.html",
                           status=status,
                           submitted=submitted,
                           ideas=all_ideas,
                           reviews=all_reviews,
                           current_user=current_user)

@app.route("/register", methods=["POST"])
def register():
    # ── pull all fields safely with .get() so missing fields return None gracefully ──
    first_name = request.form.get("first_name", "").strip()
    last_name  = request.form.get("last_name",  "").strip()
    username   = request.form.get("username",   "").strip()
    contact    = request.form.get("contact",    "").strip()
    password   = request.form.get("password",   "").strip()

    # basic validation — don't save if username or contact is empty
    if not username or not contact or not password:
        return redirect(url_for('login') + "?status=reg_error")

    # check duplicate username
    if os.path.exists("users.csv"):
        with open("users.csv", "r") as f:
            for row in csv.DictReader(f):
                if row.get("Username", "").lower() == username.lower():
                    return redirect(url_for('login') + "?status=username_taken")

    # save new user
    with open("users.csv", "a", newline="") as f:
        csv.writer(f).writerow([contact, username, password, "0", first_name, last_name])

    return redirect(url_for('login'))

@app.route("/login_check", methods=["POST"])
def login_check():
    u = request.form.get("username", "").strip()
    p = request.form.get("password", "").strip()

    if os.path.exists("users.csv"):
        with open("users.csv", "r") as f:
            for row in csv.DictReader(f):
                # allow login by username OR email
                if (row.get("Username") == u or row.get("Email") == u) and row.get("Password") == p:
                    session['username'] = row["Username"]
                    return redirect(url_for('login', status='success'))

    return redirect(url_for('login', status='failed'))

@app.route("/share_idea", methods=["POST"])
def share_idea():
    data = [
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
    ]
    with open("ideas.csv", "a", newline="") as f:
        csv.writer(f).writerow(data)
    return redirect(url_for('login', status='success', submitted='idea'))

@app.route("/submit_review", methods=["POST"])
def submit_review():
    data = [
        request.form.get("idea_title",  "").strip(),
        request.form.get("innovation",  "3"),
        request.form.get("feasibility", "3"),
        request.form.get("usefulness",  "3"),
        request.form.get("clarity",     "3"),
        request.form.get("notes",       "").strip(),
        session.get('username', 'Guest')
    ]
    with open("reviews.csv", "a", newline="") as f:
        csv.writer(f).writerow(data)
    return redirect(url_for('login', status='success', submitted='review'))

@app.route("/export_pdf/<title>")
def export_pdf(title):
    return f"Generating PDF for {title}... (Feature coming soon)", 200

if __name__ == "__main__":
    app.run(debug=True)