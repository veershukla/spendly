# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spendly** is a personal expense tracking web app built with Flask. The project is structured as a guided 9-step learning exercise — the frontend is complete, while the backend is progressively implemented step by step.

## Commands

```bash
# Activate virtual environment (required before running anything)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server (http://localhost:5001)
python app.py

# Run tests
pytest
pytest -v                          # verbose
pytest tests/test_auth.py          # single file
pytest -k "test_login"             # single test by name
```

## Architecture

**Stack:** Flask 3.1.x + Jinja2 templates + SQLite (via Python's `sqlite3`) + vanilla JS/CSS

**Single-file backend:** All routes live in `app.py`. No blueprints — keep it this way for the current scope.

**Database module:** `database/db.py` is the stub for `get_db()`, `init_db()`, and `seed_db()`. SQLite is the intended backend (no ORM).

**Templates** extend `templates/base.html`, which defines navbar, footer, and Jinja block structure (`block content`, etc.).

**Static assets:** `static/css/style.css` has global styles; `static/css/landing.css` is landing-page-specific. `static/js/main.js` is currently empty.

## Implementation Roadmap

The 9-step progression (reflected in placeholder routes in `app.py`):

1. Database setup (`database/db.py`)
2. Auth POST handlers (`/register`, `/login`)
3. Logout (`/logout`)
4. Profile page (`/profile`)
5–6. Dashboard / expense list (implied)
7. Add expense (`/expenses/add`)
8. Edit expense (`/expenses/<id>/edit`)
9. Delete expense (`/expenses/<id>/delete`)

Placeholder routes currently return plain-text strings like `"Add expense — coming in Step 7"`.

## Design System

CSS custom properties defined in `style.css`:
- `--ink: #0f0f0f` — primary text
- `--accent: #1a472a` — brand green
- `--accent-2: #c17f24` — secondary orange
- `--danger: #c0392b` — destructive actions
- `--paper: #f7f6f3` — background
- `--border: #e4e1da` — borders

Fonts: DM Serif Display (headings) + DM Sans (body) via Google Fonts, loaded in `base.html`.

## Key Notes

- `Werkzeug` is already a dependency — use `werkzeug.security` for password hashing when implementing auth.
- `pytest-flask` is installed — use its `client` fixture for route testing.
- No `.env` file exists yet; if adding secrets (e.g. `SECRET_KEY`), document the variable in a `.env.example`.
