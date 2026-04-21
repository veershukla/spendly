import os

from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("register.html")

    name             = request.form.get("name", "").strip()
    email            = request.form.get("email", "").strip()
    password         = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name:
        return render_template("register.html", error="Name is required.")
    if not email:
        return render_template("register.html", error="Email is required.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        conn.close()
        return render_template("register.html", error="An account with that email already exists.")

    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    user = conn.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Email and password are required.")

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile", methods=["GET"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Demo User",
        "email": "demo@spendly.com",
        "member_since": "2026-04-20",
        "initials": "DU",
    }
    summary = {
        "total_spent": 6165.00,
        "transaction_count": 8,
        "top_category": "Shopping",
        "top_amount": 2200.00,
    }
    transactions = [
        {"date": "2026-04-01", "description": "Grocery run",       "category": "Food",          "amount": 450.00},
        {"date": "2026-04-02", "description": "Metro card top-up", "category": "Transport",     "amount": 120.00},
        {"date": "2026-04-04", "description": "Electricity bill",  "category": "Bills",         "amount": 1800.00},
        {"date": "2026-04-06", "description": "Pharmacy",          "category": "Health",        "amount": 650.00},
        {"date": "2026-04-07", "description": "Movie tickets",     "category": "Entertainment", "amount": 300.00},
        {"date": "2026-04-09", "description": "Clothes",           "category": "Shopping",      "amount": 2200.00},
        {"date": "2026-04-10", "description": "Miscellaneous",     "category": "Other",         "amount": 85.00},
        {"date": "2026-04-12", "description": "Restaurant dinner", "category": "Food",          "amount": 560.00},
    ]
    categories = [
        {"name": "Shopping",      "total": 2200.00, "pct": 36},
        {"name": "Bills",         "total": 1800.00, "pct": 29},
        {"name": "Food",          "total": 1010.00, "pct": 16},
        {"name": "Health",        "total": 650.00,  "pct": 11},
        {"name": "Entertainment", "total": 300.00,  "pct": 5},
        {"name": "Transport",     "total": 120.00,  "pct": 2},
        {"name": "Other",         "total": 85.00,   "pct": 1},
    ]
    return render_template("profile.html", user=user, summary=summary,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
