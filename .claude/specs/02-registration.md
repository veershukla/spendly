# Spec: Registration

## Overview
Implement the POST handler for `/register` so new users can create a Spendly account. The GET route and `register.html` template already exist — this step wires up form submission: validates input, checks for duplicate emails, hashes the password, inserts the user into the database, starts a session, and redirects to the dashboard (or login). This is the first step that introduces Flask sessions and user state to the app.

## Depends on
- Step 1 — Database setup (`database/db.py`, `users` table, `get_db()`)

## Routes
- `GET /register` — render registration form — public (already exists, no change needed)
- `POST /register` — handle form submission, create user, start session — public

## Database changes
No database changes. The `users` table already has all required columns (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates
- **Modify:** `templates/register.html` — ensure the form has `method="POST"` and `action="/register"`, with `name` fields matching: `name`, `email`, `password`, `confirm_password`. Display flash messages for errors and success.

## Files to change
- `app.py` — add POST handler to the existing `/register` route; import `session`, `redirect`, `url_for`, `request`, `flash` from Flask; set `app.secret_key`
- `templates/register.html` — verify/add form attributes and flash message rendering

## Files to create
- `.env.example` — document the `SECRET_KEY` variable

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` must be set — read from environment or fall back to a dev default; document in `.env.example`
- On duplicate email, flash a user-friendly error and re-render the form — do not raise an unhandled exception
- Validate that `password == confirm_password` before inserting
- Validate that `name` and `email` are non-empty
- After successful registration, store `user_id` and `user_name` in `session` and redirect to `/dashboard` (placeholder is fine for now)

## Definition of done
- [ ] Submitting the form with valid data creates a new row in `users` with a hashed password
- [ ] Submitting with a duplicate email re-renders the form with an error message — no duplicate row inserted
- [ ] Submitting with mismatched passwords re-renders the form with an error message
- [ ] Submitting with empty name or email re-renders the form with an error message
- [ ] After successful registration, `session['user_id']` is set
- [ ] After successful registration, the user is redirected (302) away from `/register`
- [ ] App starts without errors and `SECRET_KEY` is documented in `.env.example`
- [ ] All SQL uses parameterised queries
