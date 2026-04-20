# Spec: Login and Logout

## Overview
Implement the POST handler for `/login` so existing users can authenticate, and wire up `/logout` to clear the session. The GET route and `login.html` template already exist — this step adds form submission: validates credentials, verifies the hashed password, starts a session on success, and redirects to the dashboard. Logout clears the session entirely and redirects to the landing page. Together these two routes complete the authentication loop started in Step 2.

## Depends on
- Step 1 — Database setup (`database/db.py`, `users` table, `get_db()`)
- Step 2 — Registration (user rows exist in `users` table with `password_hash`)

## Routes
- `GET /login` — render login form — public (already exists, no change needed)
- `POST /login` — validate credentials, start session, redirect to dashboard — public
- `GET /logout` — clear session, redirect to landing page — logged-in (redirect to `/login` if not authenticated)

## Database changes
No database changes. The `users` table already has all required columns.

## Templates
- **Modify:** `templates/login.html` — ensure the form has `method="POST"` and `action="/login"`, with `name` fields matching: `email`, `password`. Display error messages for failed login attempts.

## Files to change
- `app.py` — add POST handler to the existing `/login` route; implement `/logout` route; import `check_password_hash` from `werkzeug.security`

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never use string formatting in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- On failed login (bad email or wrong password), show a single generic error message ("Invalid email or password") — do not reveal which field was wrong
- After successful login, store `user_id` and `user_name` in `session` and redirect to `/dashboard` (placeholder is fine for now)
- Logout must call `session.clear()` and redirect to `url_for('landing')`
- Do not expose whether an email exists in the database via error messaging (prevents user enumeration)

## Definition of done
- [ ] Submitting valid credentials sets `session['user_id']` and redirects (302) away from `/login`
- [ ] Submitting an unknown email re-renders the form with a generic error — no traceback
- [ ] Submitting a known email with wrong password re-renders the form with the same generic error
- [ ] Submitting with empty email or password re-renders the form with an error message
- [ ] Visiting `/logout` clears the session and redirects to the landing page
- [ ] After logout, `session.get('user_id')` returns `None`
- [ ] All SQL uses parameterised queries
