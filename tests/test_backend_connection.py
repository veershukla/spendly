from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(app, demo_user_id):
    user = get_user_by_id(demo_user_id)
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["initials"] == "DU"
    assert "member_since" in user
    assert user["member_since"] != ""


def test_get_user_by_id_nonexistent(app):
    assert get_user_by_id(9999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                   #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(app, demo_user_id):
    stats = get_summary_stats(demo_user_id)
    assert stats["total_spent"] == pytest.approx(6165.00)
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Shopping"
    assert stats["top_amount"] == pytest.approx(2200.00)


def test_get_summary_stats_no_expenses(app):
    from database.db import get_db
    from werkzeug.security import generate_password_hash

    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@spendly.com", generate_password_hash("pass1234")),
    )
    conn.commit()
    uid = conn.execute("SELECT id FROM users WHERE email = ?", ("empty@spendly.com",)).fetchone()[0]
    conn.close()

    stats = get_summary_stats(uid)
    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"
    assert stats["top_amount"] == 0


# ------------------------------------------------------------------ #
# get_recent_transactions                                             #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_with_expenses(app, demo_user_id):
    txs = get_recent_transactions(demo_user_id)
    assert len(txs) == 8
    dates = [t["date"] for t in txs]
    assert dates == sorted(dates, reverse=True)
    for tx in txs:
        assert {"date", "description", "category", "amount"} <= tx.keys()


def test_get_recent_transactions_no_expenses(app):
    from database.db import get_db
    from werkzeug.security import generate_password_hash

    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("No Spend", "nospend@spendly.com", generate_password_hash("pass1234")),
    )
    conn.commit()
    uid = conn.execute("SELECT id FROM users WHERE email = ?", ("nospend@spendly.com",)).fetchone()[0]
    conn.close()

    assert get_recent_transactions(uid) == []


# ------------------------------------------------------------------ #
# get_category_breakdown                                              #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_with_expenses(app, demo_user_id):
    cats = get_category_breakdown(demo_user_id)
    assert len(cats) == 7
    totals = [c["total"] for c in cats]
    assert totals == sorted(totals, reverse=True)
    assert sum(c["pct"] for c in cats) == 100
    for c in cats:
        assert isinstance(c["pct"], int)


def test_get_category_breakdown_no_expenses(app):
    from database.db import get_db
    from werkzeug.security import generate_password_hash

    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Broke", "broke@spendly.com", generate_password_hash("pass1234")),
    )
    conn.commit()
    uid = conn.execute("SELECT id FROM users WHERE email = ?", ("broke@spendly.com",)).fetchone()[0]
    conn.close()

    assert get_category_breakdown(uid) == []


# ------------------------------------------------------------------ #
# Route: GET /profile                                                 #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated(client, app, demo_user_id):
    with client.session_transaction() as sess:
        sess["user_id"]   = demo_user_id
        sess["user_name"] = "Demo User"

    resp = client.get("/profile")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body


import pytest
