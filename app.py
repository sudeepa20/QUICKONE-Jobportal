from flask import Flask, render_template, request, redirect, session, g, url_for, flash
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='templates')
app.secret_key = "your_secret_key"
DATABASE = "quickone.db"

# File upload configuration
UPLOAD_FOLDER = 'static/logos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    # Create users table
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """)

    # Create admin table
    db.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        Ad_uname TEXT UNIQUE NOT NULL,
        Ad_pass TEXT NOT NULL
    );
    """)

    # Create jobs table
    db.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        job_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        job_name TEXT NOT NULL,
        job_type TEXT NOT NULL,
        location TEXT NOT NULL,
        job_offer REAL NOT NULL,
        job_description TEXT NOT NULL,
        logo TEXT,
        link TEXT,
        expiry_date TIMESTAMP NOT NULL
    );
    """)

    # Insert predefined admin details (if not already present)
    db.execute("""
    INSERT OR IGNORE INTO admins (Ad_uname, Ad_pass) VALUES ('admin', 'admin123');
    """)
    db.commit()

# ==============================
# Route to Insert Job (Admin Side)
# ==============================
@app.route("/add_job", methods=["POST"])
def add_job():
    if "admin" not in session:
        return redirect(url_for("adminlogin"))

    company_name = request.form.get("company_name", "").strip()
    job_name = request.form.get("job_name", "").strip()
    job_type = request.form.get("job_type", "").strip()
    location = request.form.get("location", "").strip()
    job_offer = request.form.get("job_offer", "").strip()
    job_description = request.form.get("job_description", "").strip()
    link = request.form.get("link", "").strip()

    # ✅ Set expiry date for 10 days from today
    expiry_date = datetime.now() + timedelta(days=10)

    logo = None
    if 'company_logo' in request.files:
        file = request.files['company_logo']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            logo = filename

    if not (company_name and job_name and job_type and location and job_offer and job_description and link):
        flash("All fields are required.")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    db.execute("""
        INSERT INTO jobs (company_name, job_name, job_type, location, job_offer, job_description, logo, link, expiry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (company_name, job_name, job_type, location, job_offer, job_description, logo, link, expiry_date))
    db.commit()

    flash("Job added successfully!")
    return redirect(url_for("admin_dashboard"))

# ==============================
# Route to Display Jobs on User Page
# ==============================
@app.route("/jobs", methods=["GET"])
def jobs():
    db = get_db()
    jobs = db.execute("SELECT * FROM jobs WHERE expiry_date >= CURRENT_TIMESTAMP").fetchall()
    return render_template("job.html", jobs=jobs)

# ==============================
# Route to Display Job Details
# ==============================
@app.route('/job_details/<int:job_id>')
def job_details(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    
    if not job:
        return "Job not found", 404
    
    return render_template("job_details.html", job=job)
# ==============================
# Route to Update Job
# ==============================
@app.route("/update_job/<int:job_id>", methods=["GET", "POST"])
def update_job(job_id):
    if "admin" not in session:
        return redirect(url_for("adminlogin"))

    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

    if request.method == "POST":
        company_name = request.form.get("company_name", "").strip()
        job_name = request.form.get("job_name", "").strip()
        job_type = request.form.get("job_type", "").strip()
        location = request.form.get("location", "").strip()
        job_offer = request.form.get("job_offer", "").strip()
        job_description = request.form.get("job_description", "").strip()
        link = request.form.get("link", "").strip()

        logo = job["logo"]
        if 'company_logo' in request.files:
            file = request.files['company_logo']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                logo = filename

        if not (company_name and job_name and job_type and location and job_offer and job_description and link):
            flash("All fields are required.")
            return redirect(url_for("update_job", job_id=job_id))

        db.execute("""
            UPDATE jobs
            SET company_name = ?, job_name = ?, job_type = ?, location = ?, job_offer = ?, job_description = ?, logo = ?, link = ?
            WHERE job_id = ?
        """, (company_name, job_name, job_type, location, job_offer, job_description, logo, link, job_id))
        db.commit()

        flash("Job updated successfully!")
        return redirect(url_for("admin_dashboard"))

    return render_template("update_job.html", job=job)


# ==============================
# Route to Delete Job
# ==============================
@app.route("/delete_job/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    if "admin" not in session:
        return redirect(url_for("adminlogin"))

    db = get_db()
    db.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
    db.commit()

    flash("Job deleted successfully!")
    return redirect(url_for("admin_dashboard"))

# ✅ Function to delete expired jobs
def delete_expired_jobs():
    db = get_db()
    db.execute("DELETE FROM jobs WHERE expiry_date < CURRENT_TIMESTAMP")
    db.commit()

# ==============================
# Forgot Password Route
# ==============================
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if new_password != confirm_password:
            return render_template("forgot.html", error="Passwords do not match.")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ? AND email = ?", (username, email)).fetchone()

        if user:
            db.execute("UPDATE users SET password = ? WHERE username = ? AND email = ?",
                       (new_password, username, email))
            db.commit()
            flash("Password updated successfully!")
            return redirect(url_for("login"))

    return render_template("forgot.html")

# ==============================
# Admin Dashboard Route
# ==============================
@app.route("/admin-dashboard", methods=["GET"])
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("adminlogin"))
    
    db = get_db()
    jobs = db.execute("SELECT * FROM jobs").fetchall()
    return render_template("admindashboard.html", jobs=jobs)

# ==============================
# Login and Registration
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("login.html", error="Username and password are required!")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and user["password"] == password:
            session["username"] = user["username"]
            session.permanent = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            return render_template("register.html", error="All fields are required.")

        db = get_db()
        try:
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, password))
            db.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username or email already exists.")

    return render_template("register.html")

# ==============================
# Admin Login Route
# ==============================
@app.route("/admin-login", methods=["GET", "POST"])
def adminlogin():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("adminlogin.html", error="Username and password are required!")

        db = get_db()
        admin = db.execute("SELECT * FROM admins WHERE Ad_uname = ? AND Ad_pass = ?", (username, password)).fetchone()

        if admin:
            session["admin"] = admin["Ad_uname"]
            session.permanent = True
            flash("Login successful!")
            return redirect(url_for("admin_dashboard"))  # ✅ Renders dashboard after login
        else:
            flash("Invalid username or password.")
            return render_template("adminlogin.html", error="Invalid username or password.")

    return render_template("adminlogin.html")


# ==============================
# Contact and About Routes
# ==============================
@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/about")
def about():
    return render_template("about.html")

# ==============================
# Index Route
# ==============================
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# ==============================
# Logout Route
# ==============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ==============================
# Close DB Connection
# ==============================
@app.teardown_appcontext
def close_connection(exception):
    delete_expired_jobs()  # ✅ Auto-delete expired jobs
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True)