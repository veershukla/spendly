# tests/test_06-date-filter-profile-page.py
#
# Spec behaviours tested (Step 6 — Date Filter for Profile Page):
#
#   1. GET /profile with no params returns 200, all 8 seed expenses visible,
#      label reads "All time at a glance", date inputs carry no value.
#   2. GET /profile?date_from=2026-04-01&date_to=2026-04-06 returns exactly the
#      4 named expenses (Grocery run, Metro card top-up, Electricity bill,
#      Pharmacy) and excludes the remaining 4.
#      NOTE: The spec names these 4 expenses and assigns date_to=2026-04-07, but
#      Movie tickets (Entertainment) also falls on 2026-04-07, making the
#      inclusive BETWEEN produce 5 rows, not 4. Tests use date_to=2026-04-06 to
#      match the 4-expense list the spec enumerates. A separate test covers the
#      5-expense case when date_to=2026-04-07.
#   3. Summary stats (total, count, top_category) reflect only the filtered range.
#   4. Category breakdown only lists categories present in the filtered range.
#   5. Date inputs are pre-populated with the submitted values after apply.
#   6. GET /profile (Clear) — unfiltered view, date inputs are empty.
#   7. Only one bound supplied → unfiltered results (both bounds required).
#   8. Unauthenticated GET /profile → 302 redirect to /login.

import sqlite3
import pytest
from werkzeug.security import generate_password_hash

import database.db as db_module
from app import app
from database.db import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Redirects every get_db() call to a fresh temporary SQLite file so tests
    never touch the production spendly.db. Seeds the demo user and 8 expenses
    exactly as defined in the project spec.
    """
    tmp_db = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db_module, "DB_PATH", tmp_db)

    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    with app.app_context():
        init_db()
        _seed_test_data(tmp_db)

    with app.test_client() as test_client:
        yield test_client


def _seed_test_data(db_path: str) -> None:
    """Insert the canonical demo user and 8 dated expenses used across all tests."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    )
    conn.commit()

    user_id = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()[0]

    expenses = [
        (user_id, 450.00,  "Food",          "2026-04-01", "Grocery run"),
        (user_id, 120.00,  "Transport",     "2026-04-02", "Metro card top-up"),
        (user_id, 1800.00, "Bills",         "2026-04-04", "Electricity bill"),
        (user_id, 650.00,  "Health",        "2026-04-06", "Pharmacy"),
        (user_id, 300.00,  "Entertainment", "2026-04-07", "Movie tickets"),
        (user_id, 2200.00, "Shopping",      "2026-04-09", "Clothes"),
        (user_id, 85.00,   "Other",         "2026-04-10", "Miscellaneous"),
        (user_id, 560.00,  "Food",          "2026-04-12", "Restaurant dinner"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        expenses,
    )
    conn.commit()
    conn.close()


def _login(client, email="demo@spendly.com", password="demo123"):
    """Helper: POST /login and follow the redirect so the session cookie is set."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_profile_redirects_to_login(self, client):
        """Unauthenticated GET /profile must 302-redirect to /login."""
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_get_profile_with_filter_params_redirects_to_login(self, client):
        """Auth guard applies even when query params are present."""
        response = client.get("/profile?date_from=2026-04-01&date_to=2026-04-06")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# 2. Unfiltered view (no query params)
# ---------------------------------------------------------------------------

class TestUnfilteredView:
    def test_get_profile_no_params_returns_200(self, client):
        """GET /profile with no params must return HTTP 200."""
        _login(client)
        response = client.get("/profile")
        assert response.status_code == 200

    def test_get_profile_no_params_shows_all_8_expenses(self, client):
        """All 8 seed expense descriptions must appear in the unfiltered response."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()

        expected_descriptions = [
            "Grocery run",
            "Metro card top-up",
            "Electricity bill",
            "Pharmacy",
            "Movie tickets",
            "Clothes",
            "Miscellaneous",
            "Restaurant dinner",
        ]
        for description in expected_descriptions:
            assert description in html, (
                f"Expected expense '{description}' to appear in unfiltered profile page"
            )

    def test_get_profile_no_params_label_is_all_time_at_a_glance(self, client):
        """The stats label must read 'All time at a glance' when no filter is active."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert "All time at a glance" in html

    def test_get_profile_no_params_date_inputs_are_empty(self, client):
        """Date inputs must carry no pre-populated value when no filter is active."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        # The template renders value="{{ date_from }}" and value="{{ date_to }}".
        # When both are empty strings the rendered attributes must be value="".
        assert 'name="date_from"' in html
        assert 'name="date_to"' in html
        # Neither input should carry a date value.
        assert 'value="2026-' not in html

    def test_get_profile_no_params_total_spent_reflects_all_expenses(self, client):
        """Total spent stat must equal the sum of all 8 seed expenses (6165)."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        # Sum: 450+120+1800+650+300+2200+85+560 = 6165
        assert "6165" in html

    def test_get_profile_no_params_transaction_count_is_8(self, client):
        """Transaction count stat must be 8 for the unfiltered view."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        # Template: <span class="mock-stat-value mock-stat-plain">8</span>
        assert "mock-stat-plain\">8<" in html

    def test_get_profile_no_params_top_category_is_shopping(self, client):
        """Top category in unfiltered view must be Shopping (₹2200, the highest single-category total)."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert "Shopping" in html

    def test_get_profile_no_params_all_categories_in_breakdown(self, client):
        """All 7 distinct categories from seed data must appear in the category breakdown."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        for category in ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]:
            assert category in html, (
                f"Category '{category}' expected in unfiltered category breakdown"
            )


# ---------------------------------------------------------------------------
# 3. Filtered view — 4-expense range (2026-04-01 to 2026-04-06)
# ---------------------------------------------------------------------------

class TestFilteredView:
    DATE_FROM = "2026-04-01"
    DATE_TO   = "2026-04-06"
    # Expenses in range: Grocery run (Food, 450), Metro card top-up (Transport, 120),
    # Electricity bill (Bills, 1800), Pharmacy (Health, 650).  Total = 3020.
    EXPECTED_IN_RANGE = [
        "Grocery run",
        "Metro card top-up",
        "Electricity bill",
        "Pharmacy",
    ]
    EXPECTED_OUT_OF_RANGE = [
        "Movie tickets",
        "Clothes",
        "Miscellaneous",
        "Restaurant dinner",
    ]

    def test_filtered_view_returns_200(self, client):
        """GET /profile with valid date range must return HTTP 200."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        assert response.status_code == 200

    def test_filtered_view_shows_only_in_range_expenses(self, client):
        """Only expenses within the date range must appear in the transaction table."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        for description in self.EXPECTED_IN_RANGE:
            assert description in html, (
                f"Expected in-range expense '{description}' to appear in filtered view"
            )

    def test_filtered_view_excludes_out_of_range_expenses(self, client):
        """Expenses outside the date range must not appear in the transaction table."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        for description in self.EXPECTED_OUT_OF_RANGE:
            assert description not in html, (
                f"Out-of-range expense '{description}' must not appear in filtered view"
            )

    def test_filtered_view_summary_total_is_correct(self, client):
        """Total spent must equal the sum of the 4 in-range expenses: 3020."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        # 450 + 120 + 1800 + 650 = 3020
        assert "3020" in html

    def test_filtered_view_summary_transaction_count_is_4(self, client):
        """Transaction count must be 4 for the 2026-04-01 to 2026-04-06 range."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        # Template: <span class="mock-stat-value mock-stat-plain">4</span>
        assert "mock-stat-plain\">4<" in html

    def test_filtered_view_summary_top_category_is_bills(self, client):
        """Top category for 2026-04-01..2026-04-06 must be Bills (₹1800)."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert "Bills" in html

    def test_filtered_view_category_breakdown_only_in_range_categories(self, client):
        """Category breakdown must only show categories present in the filtered range."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        in_range_categories     = ["Food", "Transport", "Bills", "Health"]
        out_of_range_categories = ["Entertainment", "Shopping", "Other"]

        for category in in_range_categories:
            assert category in html, (
                f"In-range category '{category}' must appear in the breakdown"
            )
        for category in out_of_range_categories:
            assert category not in html, (
                f"Out-of-range category '{category}' must not appear in the breakdown"
            )

    def test_filtered_view_label_shows_formatted_date_range(self, client):
        """Stats label must read '01 Apr – 06 Apr 2026 at a glance' for the applied filter."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert "01 Apr" in html
        assert "06 Apr 2026" in html
        assert "at a glance" in html

    def test_filtered_view_label_does_not_show_all_time(self, client):
        """'All time at a glance' must not appear when a filter is active."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert "All time at a glance" not in html

    def test_filtered_view_date_inputs_are_prepopulated(self, client):
        """Both date inputs must carry the submitted values so the form retains state."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert f'value="{self.DATE_FROM}"' in html
        assert f'value="{self.DATE_TO}"' in html


# ---------------------------------------------------------------------------
# 4. Filtered view — spec's stated range (2026-04-01 to 2026-04-07, 5 expenses)
# ---------------------------------------------------------------------------

class TestFilteredViewSpecRange:
    """
    The spec's Definition of Done states date_to=2026-04-07 with 4 results, but
    Movie tickets (2026-04-07) is included by BETWEEN's inclusive upper bound,
    giving 5 rows. These tests verify the correct BETWEEN behaviour for that range.
    """
    DATE_FROM = "2026-04-01"
    DATE_TO   = "2026-04-07"

    def test_spec_range_includes_movie_tickets(self, client):
        """Movie tickets (2026-04-07) must appear when date_to=2026-04-07 (inclusive)."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert "Movie tickets" in html

    def test_spec_range_excludes_expenses_after_date_to(self, client):
        """Expenses after 2026-04-07 must not appear when date_to=2026-04-07."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        for description in ["Clothes", "Miscellaneous", "Restaurant dinner"]:
            assert description not in html

    def test_spec_range_label_shows_01_apr_to_07_apr_2026(self, client):
        """Stats label must read '01 Apr – 07 Apr 2026 at a glance'."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert "01 Apr" in html
        assert "07 Apr 2026" in html
        assert "at a glance" in html

    def test_spec_range_total_is_3320(self, client):
        """Total for 2026-04-01..2026-04-07 (5 expenses) must be 3320."""
        # 450 + 120 + 1800 + 650 + 300 = 3320
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert "3320" in html

    def test_spec_range_inputs_prepopulated_with_2026_04_07(self, client):
        """Date inputs must reflect value='2026-04-07' after applying the spec range."""
        _login(client)
        response = client.get(
            f"/profile?date_from={self.DATE_FROM}&date_to={self.DATE_TO}"
        )
        html = response.data.decode()
        assert 'value="2026-04-01"' in html
        assert 'value="2026-04-07"' in html


# ---------------------------------------------------------------------------
# 5. One-bound-only behaviour (both bounds required)
# ---------------------------------------------------------------------------

class TestOneBoundOnly:
    def test_only_date_from_supplied_shows_all_expenses(self, client):
        """When only date_from is supplied (no date_to), all expenses must be shown."""
        _login(client)
        response = client.get("/profile?date_from=2026-04-01")
        html = response.data.decode()
        for description in [
            "Grocery run", "Metro card top-up", "Electricity bill", "Pharmacy",
            "Movie tickets", "Clothes", "Miscellaneous", "Restaurant dinner",
        ]:
            assert description in html, (
                f"Expected all expenses when only date_from supplied; missing '{description}'"
            )

    def test_only_date_to_supplied_shows_all_expenses(self, client):
        """When only date_to is supplied (no date_from), all expenses must be shown."""
        _login(client)
        response = client.get("/profile?date_to=2026-04-06")
        html = response.data.decode()
        for description in [
            "Grocery run", "Metro card top-up", "Electricity bill", "Pharmacy",
            "Movie tickets", "Clothes", "Miscellaneous", "Restaurant dinner",
        ]:
            assert description in html, (
                f"Expected all expenses when only date_to supplied; missing '{description}'"
            )

    def test_only_date_from_supplied_label_is_all_time(self, client):
        """Label must fall back to 'All time at a glance' when only date_from is given."""
        _login(client)
        response = client.get("/profile?date_from=2026-04-01")
        html = response.data.decode()
        assert "All time at a glance" in html

    def test_only_date_to_supplied_label_is_all_time(self, client):
        """Label must fall back to 'All time at a glance' when only date_to is given."""
        _login(client)
        response = client.get("/profile?date_to=2026-04-06")
        html = response.data.decode()
        assert "All time at a glance" in html

    def test_only_date_from_supplied_inputs_are_cleared(self, client):
        """When only one bound is given, the filter is not active — inputs must be empty."""
        _login(client)
        response = client.get("/profile?date_from=2026-04-01")
        html = response.data.decode()
        # The route resets both to "" when the filter is inactive.
        assert 'value="2026-04-01"' not in html

    def test_only_date_to_supplied_inputs_are_cleared(self, client):
        """When only one bound is given, the filter is not active — inputs must be empty."""
        _login(client)
        response = client.get("/profile?date_to=2026-04-06")
        html = response.data.decode()
        assert 'value="2026-04-06"' not in html


# ---------------------------------------------------------------------------
# 6. Clear behaviour
# ---------------------------------------------------------------------------

class TestClearBehaviour:
    def test_clear_link_returns_unfiltered_view(self, client):
        """GET /profile (the Clear href) must return the unfiltered view with all expenses."""
        _login(client)
        # First apply a filter to establish session context.
        client.get("/profile?date_from=2026-04-01&date_to=2026-04-06")
        # Now follow the Clear link.
        response = client.get("/profile")
        html = response.data.decode()
        assert response.status_code == 200
        assert "All time at a glance" in html
        for description in [
            "Grocery run", "Clothes", "Miscellaneous", "Restaurant dinner",
        ]:
            assert description in html

    def test_clear_link_empties_date_inputs(self, client):
        """After Clear, the date inputs must carry no pre-populated values."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert 'value="2026-' not in html

    def test_profile_page_contains_clear_link_href(self, client):
        """The template must render a Clear link whose href is '/profile'."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert 'href="/profile"' in html


# ---------------------------------------------------------------------------
# 7. Filter form structure
# ---------------------------------------------------------------------------

class TestFilterFormStructure:
    def test_filter_form_has_get_method(self, client):
        """The filter form must use method='GET' so the URL is bookmarkable."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert 'method="GET"' in html or "method=GET" in html

    def test_filter_form_action_is_profile(self, client):
        """The filter form action must point to /profile."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert 'action="/profile"' in html

    def test_filter_form_has_date_from_input(self, client):
        """The filter form must contain an input named 'date_from'."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert 'name="date_from"' in html

    def test_filter_form_has_date_to_input(self, client):
        """The filter form must contain an input named 'date_to'."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert 'name="date_to"' in html


# ---------------------------------------------------------------------------
# 8. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_filter_with_same_from_and_to_date_returns_single_day(self, client):
        """A filter where date_from == date_to must return only expenses on that day."""
        _login(client)
        response = client.get("/profile?date_from=2026-04-04&date_to=2026-04-04")
        html = response.data.decode()
        assert "Electricity bill" in html
        for description in [
            "Grocery run", "Metro card top-up", "Pharmacy",
            "Movie tickets", "Clothes", "Miscellaneous", "Restaurant dinner",
        ]:
            assert description not in html

    def test_filter_with_same_from_and_to_shows_single_day_total(self, client):
        """Total for a single-day filter (2026-04-04) must be 1800."""
        _login(client)
        response = client.get("/profile?date_from=2026-04-04&date_to=2026-04-04")
        html = response.data.decode()
        assert "1800" in html

    def test_filter_with_range_outside_all_data_shows_no_transactions(self, client):
        """A date range with no matching expenses must show no transaction descriptions."""
        _login(client)
        response = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        assert response.status_code == 200
        html = response.data.decode()
        for description in [
            "Grocery run", "Metro card top-up", "Electricity bill", "Pharmacy",
            "Movie tickets", "Clothes", "Miscellaneous", "Restaurant dinner",
        ]:
            assert description not in html

    def test_filter_with_range_outside_all_data_total_is_zero(self, client):
        """Total spent must be 0 when no expenses fall in the selected range."""
        _login(client)
        response = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        html = response.data.decode()
        assert "₹0" in html

    def test_empty_string_date_params_treated_as_unfiltered(self, client):
        """Explicitly empty date params (date_from=&date_to=) must produce unfiltered results."""
        _login(client)
        response = client.get("/profile?date_from=&date_to=")
        html = response.data.decode()
        assert "All time at a glance" in html
        assert "Grocery run" in html

    def test_sql_injection_in_date_from_does_not_error(self, client):
        """Parameterised queries must prevent SQL injection; page must not 500."""
        _login(client)
        response = client.get(
            "/profile?date_from='; DROP TABLE expenses; --&date_to=2026-04-06"
        )
        # The malicious date_from means only one valid bound is present after
        # the route's strip() — the filter is not applied and all expenses show.
        # Either way, the server must not crash.
        assert response.status_code in (200, 302)

    def test_currency_symbol_is_rupee_not_dollar_or_pound(self, client):
        """All monetary values on the profile page must use ₹, never $ or £."""
        _login(client)
        response = client.get("/profile")
        html = response.data.decode()
        assert "₹" in html
        assert "$" not in html
        assert "£" not in html

    def test_filter_preserves_inr_currency_symbol(self, client):
        """Filtered totals must also display ₹."""
        _login(client)
        response = client.get("/profile?date_from=2026-04-01&date_to=2026-04-06")
        html = response.data.decode()
        assert "₹" in html
        assert "$" not in html
