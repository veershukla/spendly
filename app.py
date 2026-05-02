import os
import re
from datetime import datetime

from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import get_db, init_db, seed_db, insert_expense
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
]

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

    uid  = session["user_id"]
    user = get_user_by_id(uid)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    date_from = request.args.get("date_from", "").strip()
    date_to   = request.args.get("date_to",   "").strip()

    if date_from and date_to:
        try:
            from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            to_dt   = datetime.strptime(date_to,   "%Y-%m-%d")
            filter_label = (
                f"{from_dt.strftime('%d %b')} – "
                f"{to_dt.strftime('%d %b')} {to_dt.strftime('%Y')}"
            )
        except ValueError:
            filter_label = "All time"
            date_from = date_to = ""
    else:
        filter_label = "All time"
        date_from = date_to = ""

    summary      = get_summary_stats(uid, date_from, date_to)
    transactions = get_recent_transactions(uid, date_from=date_from, date_to=date_to)
    categories   = get_category_breakdown(uid, date_from, date_to)

    return render_template(
        "profile.html",
        user=user, summary=summary,
        transactions=transactions, categories=categories,
        date_from=date_from, date_to=date_to,
        filter_label=filter_label,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    today = datetime.today().strftime("%Y-%m-%d")

    if request.method == "GET":
        return render_template("add_expense.html",
                               categories=ALLOWED_CATEGORIES,
                               today=today)

    amount_raw   = request.form.get("amount",      "").strip()
    category     = request.form.get("category",    "")
    expense_date = request.form.get("date",         "").strip()
    description  = request.form.get("description", "").strip()

    def redisplay(error):
        return render_template(
            "add_expense.html",
            categories=ALLOWED_CATEGORIES,
            today=today,
            error=error,
            amount=amount_raw,
            category=category,
            date=expense_date,
            description=description,
        )

    if not amount_raw:
        return redisplay("Amount is required.")
    try:
        amount = float(amount_raw)
    except ValueError:
        return redisplay("Amount must be a valid number.")
    if amount <= 0:
        return redisplay("Amount must be greater than zero.")
    if not re.fullmatch(r'\d+(\.\d{1,2})?', amount_raw):
        return redisplay("Amount must be a plain number with up to 2 decimal places.")
    if amount > 10_000_000:
        return redisplay("Amount must be less than ₹1,00,00,000.")

    if not category:
        return redisplay("Category is required.")
    if category not in ALLOWED_CATEGORIES:
        return redisplay("Please select a valid category.")

    if not expense_date:
        return redisplay("Date is required.")
    try:
        datetime.strptime(expense_date, "%Y-%m-%d")
    except ValueError:
        return redisplay("Date must be a valid date (YYYY-MM-DD).")

    if len(description) > 200:
        return redisplay("Description must be 200 characters or fewer.")

    insert_expense(session["user_id"], amount, category, expense_date, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
