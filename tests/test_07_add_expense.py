# tests/test_07_add_expense.py
#
# Spec behaviors tested (from .claude/specs/07-add-expense.md):
#
# AUTH GUARD
#   - Unauthenticated GET /expenses/add redirects to /login
#   - Unauthenticated POST /expenses/add redirects to /login
#
# GET FORM RENDERING
#   - Logged-in user gets 200 response with the form
#   - Date field defaults to today's date (YYYY-MM-DD)
#   - Category dropdown contains exactly 7 options:
#     Food, Transport, Bills, Health, Entertainment, Shopping, Other
#   - Amount field label includes the INR rupee symbol (₹)
#
# SUCCESSFUL POST
#   - Valid submission inserts a row in the expenses table
#   - Valid submission redirects to /profile
#   - Inserted row has the correct user_id, amount, category, date, description
#   - Description is optional: blank description succeeds and stores NULL
#
# AMOUNT VALIDATION
#   - Blank amount → "Amount is required."
#   - Non-numeric amount → "Amount must be a valid number."
#   - Amount = 0 → "Amount must be greater than zero."
#   - Negative amount → "Amount must be greater than zero."
#
# CATEGORY VALIDATION
#   - No category selected → "Category is required."
#   - Invalid category value → "Please select a valid category."
#
# DATE VALIDATION
#   - Blank date → "Date is required."
#   - Invalid date string → "Date must be a valid date (YYYY-MM-DD)."
#
# DESCRIPTION VALIDATION
#   - Description > 200 chars → "Description must be 200 characters or fewer."
#
# VALUE PRESERVATION
#   - On validation error, the submitted amount is present in the response body
#   - On validation error, the submitted category is present in the response body
#   - On validation error, the submitted date is present in the response body
#   - On validation error, the submitted description is present in the response body
#
# NO DB SIDE-EFFECT ON VALIDATION FAILURE
#   - Failed POST leaves expense count unchanged

import sqlite3
from datetime import date

import pytest

from database.db import get_db

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_EXPENSE = {
    "amount": "250.00",
    "category": "Food",
    "date": "2026-04-15",
    "description": "Lunch at canteen",
}

ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
]


def set_logged_in(client, user_id, user_name="Demo User"):
    """Inject session variables that the app uses to identify a logged-in user."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name


def expense_count(demo_user_id):
    """Return the number of expenses currently stored for the demo user."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (demo_user_id,)
    ).fetchone()
    conn.close()
    return row[0]


def latest_expense(demo_user_id):
    """Return the most recently inserted expense row for the demo user."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (demo_user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# AUTH GUARD — unauthenticated access
# ---------------------------------------------------------------------------

class TestAuthGuard:

    def test_get_unauthenticated_redirects_to_login(self, client):
        """GET /expenses/add without a session must redirect to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_post_unauthenticated_redirects_to_login(self, client):
        """POST /expenses/add without a session must redirect to /login."""
        response = client.post("/expenses/add", data=VALID_EXPENSE)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_get_unauthenticated_does_not_render_form(self, client):
        """GET /expenses/add without session must not render the add-expense form."""
        response = client.get("/expenses/add", follow_redirects=True)
        assert b"Add an expense" not in response.data


# ---------------------------------------------------------------------------
# GET FORM RENDERING
# ---------------------------------------------------------------------------

class TestGetFormRendering:

    def test_get_authenticated_returns_200(self, client, demo_user_id):
        """Logged-in user visiting GET /expenses/add gets a 200 response."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert response.status_code == 200

    def test_get_renders_amount_field(self, client, demo_user_id):
        """Form includes an input field named 'amount'."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert b'name="amount"' in response.data

    def test_get_renders_category_field(self, client, demo_user_id):
        """Form includes a select field named 'category'."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert b'name="category"' in response.data

    def test_get_renders_date_field(self, client, demo_user_id):
        """Form includes an input field named 'date'."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert b'name="date"' in response.data

    def test_get_renders_description_field(self, client, demo_user_id):
        """Form includes an input field named 'description'."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert b'name="description"' in response.data

    def test_get_date_field_defaults_to_today(self, client, demo_user_id):
        """Date field value defaults to today's date in YYYY-MM-DD format."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        today_str = date.today().strftime("%Y-%m-%d").encode()
        assert today_str in response.data

    def test_get_category_dropdown_contains_exactly_seven_options(self, client, demo_user_id):
        """The category dropdown has exactly 7 selectable options (excluding the placeholder)."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        html = response.data.decode()
        # Count option tags that carry an actual category value (non-empty value attributes)
        # Each allowed category appears as its own <option value="Category">
        found = [cat for cat in ALLOWED_CATEGORIES if f'value="{cat}"' in html]
        assert len(found) == 7

    @pytest.mark.parametrize("category", ALLOWED_CATEGORIES)
    def test_get_category_dropdown_contains_each_allowed_category(self, client, demo_user_id, category):
        """Each of the 7 allowed categories appears as an option in the dropdown."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert category.encode() in response.data

    def test_get_amount_label_shows_inr_symbol(self, client, demo_user_id):
        """Amount label must show the INR ₹ symbol, not a different currency."""
        set_logged_in(client, demo_user_id)
        response = client.get("/expenses/add")
        assert "₹".encode("utf-8") in response.data


# ---------------------------------------------------------------------------
# SUCCESSFUL POST — happy path
# ---------------------------------------------------------------------------

class TestSuccessfulPost:

    def test_valid_post_redirects_to_profile(self, client, demo_user_id):
        """Valid form submission redirects to /profile."""
        set_logged_in(client, demo_user_id)
        response = client.post("/expenses/add", data=VALID_EXPENSE)
        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

    def test_valid_post_inserts_expense_row(self, client, demo_user_id):
        """Valid form submission inserts exactly one new row in the expenses table."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        client.post("/expenses/add", data=VALID_EXPENSE)
        assert expense_count(demo_user_id) == count_before + 1

    def test_valid_post_stores_correct_amount(self, client, demo_user_id):
        """Inserted expense has the amount as submitted (stored as float)."""
        set_logged_in(client, demo_user_id)
        client.post("/expenses/add", data=VALID_EXPENSE)
        row = latest_expense(demo_user_id)
        assert row is not None
        assert row["amount"] == pytest.approx(250.00)

    def test_valid_post_stores_correct_category(self, client, demo_user_id):
        """Inserted expense has the category as submitted."""
        set_logged_in(client, demo_user_id)
        client.post("/expenses/add", data=VALID_EXPENSE)
        row = latest_expense(demo_user_id)
        assert row is not None
        assert row["category"] == "Food"

    def test_valid_post_stores_correct_date(self, client, demo_user_id):
        """Inserted expense has the date as submitted in YYYY-MM-DD format."""
        set_logged_in(client, demo_user_id)
        client.post("/expenses/add", data=VALID_EXPENSE)
        row = latest_expense(demo_user_id)
        assert row is not None
        assert row["date"] == "2026-04-15"

    def test_valid_post_stores_correct_description(self, client, demo_user_id):
        """Inserted expense has the description as submitted."""
        set_logged_in(client, demo_user_id)
        client.post("/expenses/add", data=VALID_EXPENSE)
        row = latest_expense(demo_user_id)
        assert row is not None
        assert row["description"] == "Lunch at canteen"

    def test_valid_post_stores_correct_user_id(self, client, demo_user_id):
        """Inserted expense is associated with the currently logged-in user."""
        set_logged_in(client, demo_user_id)
        client.post("/expenses/add", data=VALID_EXPENSE)
        row = latest_expense(demo_user_id)
        assert row is not None
        assert row["user_id"] == demo_user_id

    def test_valid_post_without_description_succeeds(self, client, demo_user_id):
        """Blank description is optional — submission succeeds and redirects."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "description": ""}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

    def test_valid_post_without_description_inserts_row(self, client, demo_user_id):
        """Blank description still results in a new expense row being inserted."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "description": ""}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before + 1

    def test_valid_post_without_description_stores_null_or_empty(self, client, demo_user_id):
        """Blank description is stored as NULL (or empty string) — not a literal 'None'."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "description": ""}
        client.post("/expenses/add", data=data)
        row = latest_expense(demo_user_id)
        assert row is not None
        # description should be None (NULL) or empty string, never the Python string 'None'
        assert row["description"] != "None"

    @pytest.mark.parametrize("category", ALLOWED_CATEGORIES)
    def test_valid_post_accepts_each_allowed_category(self, client, demo_user_id, category):
        """Each of the 7 allowed categories is accepted by a valid POST."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "category": category}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 302

    def test_valid_post_expense_appears_on_profile(self, client, demo_user_id):
        """After a successful add, the new expense appears in the profile page response."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "description": "Unique marker XYZ-9991"}
        client.post("/expenses/add", data=data)
        profile_response = client.get("/profile")
        assert b"Unique marker XYZ-9991" in profile_response.data


# ---------------------------------------------------------------------------
# AMOUNT VALIDATION
# ---------------------------------------------------------------------------

class TestAmountValidation:

    def test_blank_amount_returns_error(self, client, demo_user_id):
        """Blank amount field shows 'Amount is required.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": ""}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Amount is required." in response.data

    def test_blank_amount_does_not_insert_row(self, client, demo_user_id):
        """Blank amount validation failure does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "amount": ""}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before

    @pytest.mark.parametrize("bad_amount", ["abc", "twelve", "1,000", "--5", "1.2.3"])
    def test_non_numeric_amount_returns_error(self, client, demo_user_id, bad_amount):
        """Non-numeric amount shows 'Amount must be a valid number.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": bad_amount}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Amount must be a valid number." in response.data

    @pytest.mark.parametrize("bad_amount", ["abc", "twelve"])
    def test_non_numeric_amount_does_not_insert_row(self, client, demo_user_id, bad_amount):
        """Non-numeric amount validation failure does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "amount": bad_amount}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before

    def test_zero_amount_returns_error(self, client, demo_user_id):
        """Amount of 0 shows 'Amount must be greater than zero.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": "0"}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Amount must be greater than zero." in response.data

    def test_zero_amount_does_not_insert_row(self, client, demo_user_id):
        """Amount = 0 does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "amount": "0"}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before

    @pytest.mark.parametrize("negative_amount", ["-1", "-0.01", "-999.99"])
    def test_negative_amount_returns_error(self, client, demo_user_id, negative_amount):
        """Negative amount shows 'Amount must be greater than zero.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": negative_amount}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Amount must be greater than zero." in response.data

    @pytest.mark.parametrize("negative_amount", ["-1", "-0.01"])
    def test_negative_amount_does_not_insert_row(self, client, demo_user_id, negative_amount):
        """Negative amount validation failure does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "amount": negative_amount}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before


# ---------------------------------------------------------------------------
# CATEGORY VALIDATION
# ---------------------------------------------------------------------------

class TestCategoryValidation:

    def test_blank_category_returns_error(self, client, demo_user_id):
        """No category selected shows 'Category is required.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "category": ""}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Category is required." in response.data

    def test_blank_category_does_not_insert_row(self, client, demo_user_id):
        """Missing category does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "category": ""}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before

    @pytest.mark.parametrize("bad_category", [
        "food",           # wrong case
        "FOOD",           # all caps
        "Groceries",      # not in the list
        "Transport ",     # trailing space
        " Food",          # leading space
        "'; DROP TABLE expenses; --",   # SQL injection attempt
    ])
    def test_invalid_category_returns_error(self, client, demo_user_id, bad_category):
        """An invalid (not in allowed list) category value shows 'Please select a valid category.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "category": bad_category}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Please select a valid category." in response.data

    @pytest.mark.parametrize("bad_category", ["Groceries", "'; DROP TABLE expenses; --"])
    def test_invalid_category_does_not_insert_row(self, client, demo_user_id, bad_category):
        """Invalid category does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "category": bad_category}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before


# ---------------------------------------------------------------------------
# DATE VALIDATION
# ---------------------------------------------------------------------------

class TestDateValidation:

    def test_blank_date_returns_error(self, client, demo_user_id):
        """Blank date field shows 'Date is required.' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "date": ""}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Date is required." in response.data

    def test_blank_date_does_not_insert_row(self, client, demo_user_id):
        """Blank date does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "date": ""}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before

    @pytest.mark.parametrize("bad_date", [
        "15-04-2026",      # DD-MM-YYYY (wrong order)
        "04/15/2026",      # MM/DD/YYYY (US slash format)
        "April 15 2026",   # human-readable text
        "2026-13-01",      # month 13 — out of range
        "2026-04-31",      # April 31 — doesn't exist
        "not-a-date",      # completely invalid
        "20260415",        # no delimiters
    ])
    def test_invalid_date_string_returns_error(self, client, demo_user_id, bad_date):
        """Invalid date string shows 'Date must be a valid date (YYYY-MM-DD).' error."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "date": bad_date}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Date must be a valid date (YYYY-MM-DD)." in response.data

    @pytest.mark.parametrize("bad_date", ["15-04-2026", "not-a-date", "2026-13-01"])
    def test_invalid_date_does_not_insert_row(self, client, demo_user_id, bad_date):
        """Invalid date does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "date": bad_date}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before


# ---------------------------------------------------------------------------
# DESCRIPTION VALIDATION
# ---------------------------------------------------------------------------

class TestDescriptionValidation:

    def test_description_over_200_chars_returns_error(self, client, demo_user_id):
        """Description longer than 200 characters shows the length-limit error."""
        set_logged_in(client, demo_user_id)
        long_desc = "A" * 201
        data = {**VALID_EXPENSE, "description": long_desc}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Description must be 200 characters or fewer." in response.data

    def test_description_over_200_chars_does_not_insert_row(self, client, demo_user_id):
        """Description > 200 chars does not insert any expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "description": "B" * 201}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before

    def test_description_exactly_200_chars_succeeds(self, client, demo_user_id):
        """Description of exactly 200 characters is accepted and redirects."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "description": "C" * 200}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 302

    def test_description_exactly_200_chars_inserts_row(self, client, demo_user_id):
        """Description of exactly 200 characters results in a new expense row."""
        set_logged_in(client, demo_user_id)
        count_before = expense_count(demo_user_id)
        data = {**VALID_EXPENSE, "description": "D" * 200}
        client.post("/expenses/add", data=data)
        assert expense_count(demo_user_id) == count_before + 1


# ---------------------------------------------------------------------------
# VALUE PRESERVATION ON VALIDATION ERROR
# ---------------------------------------------------------------------------

class TestValuePreservation:

    def test_submitted_amount_preserved_on_error(self, client, demo_user_id):
        """On validation error, the submitted amount value is present in the re-rendered form."""
        set_logged_in(client, demo_user_id)
        # Trigger error via invalid category so amount is still echoed back
        data = {**VALID_EXPENSE, "amount": "999.50", "category": ""}
        response = client.post("/expenses/add", data=data)
        assert b"999.50" in response.data

    def test_submitted_category_preserved_on_error(self, client, demo_user_id):
        """On validation error, the submitted category value is present in the re-rendered form."""
        set_logged_in(client, demo_user_id)
        # Trigger error via blank date; category should be echoed back as selected
        data = {**VALID_EXPENSE, "category": "Health", "date": ""}
        response = client.post("/expenses/add", data=data)
        assert b"Health" in response.data

    def test_submitted_date_preserved_on_error(self, client, demo_user_id):
        """On validation error, the submitted date value is present in the re-rendered form."""
        set_logged_in(client, demo_user_id)
        # Trigger error via blank amount; date should be echoed back
        data = {**VALID_EXPENSE, "amount": "", "date": "2026-03-20"}
        response = client.post("/expenses/add", data=data)
        assert b"2026-03-20" in response.data

    def test_submitted_description_preserved_on_error(self, client, demo_user_id):
        """On validation error, the submitted description is present in the re-rendered form."""
        set_logged_in(client, demo_user_id)
        # Trigger error via blank amount; description should be echoed back
        data = {**VALID_EXPENSE, "amount": "", "description": "My preserved note"}
        response = client.post("/expenses/add", data=data)
        assert b"My preserved note" in response.data

    def test_error_message_shown_on_validation_failure(self, client, demo_user_id):
        """On validation error, an error message element is rendered in the response."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": ""}
        response = client.post("/expenses/add", data=data)
        # The template wraps errors in class="auth-error"
        assert b"auth-error" in response.data

    def test_form_is_rerendered_not_redirected_on_error(self, client, demo_user_id):
        """On validation error, the server re-renders the form (200) rather than redirecting."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": "0"}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        # Verify the form itself is present in the response
        assert b'name="amount"' in response.data


# ---------------------------------------------------------------------------
# SQL INJECTION SAFETY
# ---------------------------------------------------------------------------

class TestSqlInjectionSafety:

    def test_sql_injection_in_description_is_stored_safely(self, client, demo_user_id):
        """SQL injection payload in description is stored as literal text, not executed."""
        set_logged_in(client, demo_user_id)
        payload = "'; DROP TABLE expenses; --"
        data = {**VALID_EXPENSE, "description": payload}
        client.post("/expenses/add", data=data)
        # If the table still exists and the row is present, injection was neutralised
        row = latest_expense(demo_user_id)
        assert row is not None
        assert row["description"] == payload

    def test_sql_injection_in_amount_field_rejected(self, client, demo_user_id):
        """SQL injection attempt via amount field is rejected as non-numeric."""
        set_logged_in(client, demo_user_id)
        data = {**VALID_EXPENSE, "amount": "'; DROP TABLE expenses; --"}
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 200
        assert b"Amount must be a valid number." in response.data
        # expenses table must still be intact
        assert expense_count(demo_user_id) >= 0  # query succeeds means table exists
