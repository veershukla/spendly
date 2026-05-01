# Spec: Date Filter For Profile Page

## Overview
Step 6 adds an optional date-range filter to the `/profile` page. Users can
pick a "from" date and a "to" date; the transaction history, summary stats, and
category breakdown all update to reflect only expenses that fall within that
range. The filter is submitted as a plain GET form so the URL is bookmarkable.
When no filter is applied the page behaves exactly as it does today (all
expenses shown).

## Depends on
- Step 1: Database setup (`expenses` table with `date` column in ISO format)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page static UI (template structure already in place)
- Step 5: Backend connection (`get_summary_stats`, `get_recent_transactions`,
  `get_category_breakdown` in `database/queries.py`)

## Routes
No new routes. The existing `GET /profile` route is extended to read optional
query-string parameters:
- `?date_from=YYYY-MM-DD` — lower bound (inclusive)
- `?date_to=YYYY-MM-DD` — upper bound (inclusive)

Both params are optional. If omitted the queries are unfiltered.

## Database changes
No database changes. The `expenses.date` column already stores ISO-format
strings (`YYYY-MM-DD`), which SQLite compares correctly as text.

## Templates
- **Modify**: `templates/profile.html`
  - Add a filter bar above the summary card: two `<input type="date">` fields
    (`name="date_from"`, `name="date_to"`) and an "Apply" button inside a
    `<form method="GET" action="/profile">`.
  - Add a "Clear" link (`href="/profile"`) that resets the filter.
  - Change the hardcoded label `"April 2026 at a glance"` to a dynamic label
    that shows the active range (e.g. `"01 Apr – 30 Apr 2026 at a glance"`) or
    falls back to `"All time at a glance"` when no filter is active.
  - Pre-populate the date inputs with the currently active `date_from` /
    `date_to` values so the form retains its state after submission.

## Files to change
- `app.py` — read `date_from` and `date_to` from `request.args` in the
  `profile()` view; pass them through to all three query helpers.
- `database/queries.py` — add optional `date_from=None` and `date_to=None`
  parameters to `get_summary_stats`, `get_recent_transactions`, and
  `get_category_breakdown`; append `WHERE … AND date BETWEEN ? AND ?` clauses
  when both bounds are supplied.
- `templates/profile.html` — add filter bar UI and dynamic stats label (see
  Templates section above).

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles (the `style="width: {{ cat.pct }}%"` bar already in place
  is the existing exception; do not add new ones)
- Currency must always display as ₹ — never £ or $
- Date comparison relies on SQLite text ordering of ISO-format strings; no
  `strftime` conversion needed
- If only one bound is supplied by the user it must be silently ignored — apply
  the filter only when **both** `date_from` and `date_to` are non-empty strings
- The `date_from` / `date_to` values passed to the template must be the raw
  strings from `request.args` (or empty string `""`) so the inputs can be
  pre-populated
- The stats section label must be built in the route (not the template) and
  passed as a `filter_label` variable; format as `"DD Mon – DD Mon YYYY"` when
  both bounds are present, otherwise `"All time"`

## Definition of done
- [ ] Visiting `/profile` with no query params shows all expenses unchanged
- [ ] Submitting the filter form with `date_from=2026-04-01` and
  `date_to=2026-04-07` shows only the 4 seed expenses that fall in that range
  (Grocery run, Metro card top-up, Electricity bill, Pharmacy)
- [ ] The summary stats (total, count, top category) update to reflect only the
  filtered expenses
- [ ] The category breakdown updates to show only categories present in the
  filtered range
- [ ] The date inputs retain their values after the form is submitted
- [ ] Clicking "Clear" returns to the unfiltered view
- [ ] The stats label reads `"01 Apr – 07 Apr 2026 at a glance"` for the above
  filter and `"All time at a glance"` when no filter is set
- [ ] Submitting the form with only one date field filled in shows all expenses
  (both bounds required)
