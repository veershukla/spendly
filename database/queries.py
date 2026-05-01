from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    name = row["name"]
    initials = "".join(w[0].upper() for w in name.split()[:2])
    member_since = datetime.fromisoformat(row["created_at"]).strftime("%B %Y")
    return {
        "name": name,
        "email": row["email"],
        "member_since": member_since,
        "initials": initials,
    }


def _date_filter(date_from, date_to):
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", (date_from, date_to)
    return "", ()


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    date_clause, date_params = _date_filter(date_from, date_to)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
        "FROM expenses WHERE user_id = ?" + date_clause,
        (user_id, *date_params),
    ).fetchone()
    top = conn.execute(
        "SELECT category, SUM(amount) AS cat_total FROM expenses "
        "WHERE user_id = ?" + date_clause + " GROUP BY category ORDER BY cat_total DESC LIMIT 1",
        (user_id, *date_params),
    ).fetchone()
    conn.close()
    return {
        "total_spent": row["total"],
        "transaction_count": row["cnt"],
        "top_category": top["category"] if top else "—",
        "top_amount": top["cat_total"] if top else 0,
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conn = get_db()
    date_clause, date_params = _date_filter(date_from, date_to)
    rows = conn.execute(
        "SELECT date, description, category, amount "
        "FROM expenses WHERE user_id = ?" + date_clause + " ORDER BY date DESC LIMIT ?",
        (user_id, *date_params, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    date_clause, date_params = _date_filter(date_from, date_to)
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS total "
        "FROM expenses WHERE user_id = ?" + date_clause + " GROUP BY category ORDER BY total DESC",
        (user_id, *date_params),
    ).fetchall()
    conn.close()
    if not rows:
        return []
    grand = sum(r["total"] for r in rows)
    cats = [
        {"name": r["name"], "total": r["total"], "pct": round(r["total"] / grand * 100)}
        for r in rows
    ]
    diff = 100 - sum(c["pct"] for c in cats)
    cats[0]["pct"] += diff
    return cats
