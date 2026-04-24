import sqlite3
import pytest
from werkzeug.security import generate_password_hash

import app as flask_app_module
from database import db as db_module


SEED_EXPENSES = [
    (450.00,  "Food",          "2026-04-01", "Grocery run"),
    (120.00,  "Transport",     "2026-04-02", "Metro card top-up"),
    (1800.00, "Bills",         "2026-04-04", "Electricity bill"),
    (650.00,  "Health",        "2026-04-06", "Pharmacy"),
    (300.00,  "Entertainment", "2026-04-07", "Movie tickets"),
    (2200.00, "Shopping",      "2026-04-09", "Clothes"),
    (85.00,   "Other",         "2026-04-10", "Miscellaneous"),
    (560.00,  "Food",          "2026-04-12", "Restaurant dinner"),
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );
        CREATE TABLE expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()[0]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [(user_id, *e) for e in SEED_EXPENSES],
    )
    conn.commit()
    conn.close()

    flask_app_module.app.config["TESTING"] = True
    flask_app_module.app.config["SECRET_KEY"] = "test-secret"
    yield flask_app_module.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def demo_user_id(app):
    from database.db import get_db
    conn = get_db()
    uid = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()[0]
    conn.close()
    return uid
