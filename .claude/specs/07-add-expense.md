# Spec: Add Expense

## Overview
This step replaces the `/expenses/add` placeholder route with a fully functional form that lets a logged-in user record a new expense. The user fills in an amount, category, date, and optional description; on submission the expense is inserted into the existing `expenses` table and the user is redirected to their profile page. This is the core write path of the app — every other feature (profile stats, date filtering) depends on real expense data flowing through this route.

## Depends on
- Step 01 — Database setup (`expenses` table must exist)
- Step 02 — Registration (user accounts required)
- Step 03 — Logout (session management)
- Step 04 / 05 — Profile page (redirect destination after successful add)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert expense, redirect to profile — logged-in only

## Database changes
No database changes. The `expenses` table already exists with all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates
- **Create:** `templates/add_expense.html` — form with fields: amount, category (dropdown), date, description (optional). Shows inline error messages on validation failure.
- **Modify:** none

## Files to change
- `app.py` — replace the placeholder `add_expense` route with a GET+POST handler

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never interpolate user input into SQL strings
- Passwords hashed with werkzeug — not applicable here, but do not store plaintext
- Use CSS variables — never hardcode hex values in templates or styles
- All templates extend `base.html`
- Redirect unauthenticated users to `/login`
- Amount must be a positive number (> 0); reject zero or negative values
- Category must be one of the fixed list: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Date must be a valid date in `YYYY-MM-DD` format; default the date field to today's date
- Description is optional (max 200 chars is a reasonable soft limit — validate server-side)
- On validation error, re-render the form with the error message and the user's previously entered values preserved
- On success, redirect to `url_for("profile")`
- Amount is stored in INR (₹) — display the ₹ symbol in the form label

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders a form with Amount, Category, Date, and Description fields
- [ ] The date field defaults to today's date when the form first loads
- [ ] The Category field is a dropdown containing exactly: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- [ ] Submitting the form with a valid amount, category, and date inserts a row into the `expenses` table and redirects to `/profile`
- [ ] The new expense immediately appears in the transactions list on `/profile`
- [ ] Submitting with a blank amount shows a validation error and does not insert a row
- [ ] Submitting with amount = 0 or a negative number shows a validation error
- [ ] Submitting with a blank category shows a validation error
- [ ] Submitting with a blank date shows a validation error
- [ ] On validation error, previously entered values are preserved in the form fields
- [ ] Description field is optional — submitting without it succeeds
