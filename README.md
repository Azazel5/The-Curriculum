# The Curriculum

A small Flask app for tracking **deliberate practice** without fooling yourself. It’s built for people who have more ambition than consistency and who want the numbers to tell the truth.

---

## Why this exists

Most of us know *what* we want to get good at; fewer of us can point to **how many honest hours** we’ve put in. This app ties progress to **logged time**—not vibes—and surfaces **where you’re investing (or neglecting)** at every level of the hierarchy.

Roadmap checkboxes are a separate, honest signal: *I did what I meant to do today / for this task*, including a **daily** mode that resets each calendar day while **keeping every minute you’ve ever logged** on that row.

It’s also a humility tool. A thousand hours sounds abstract until you try to **earn** them in real weeks.

---

## Hierarchy: **Project → Curriculum → Item**

The mental model is strict top-down:

| Layer | What it is | Role |
|--------|------------|------|
| **Project** | North Star / theme | The parent bucket. Groups related curricula (e.g. “Deep learning expertise,” “Interview prep”). **The home dashboard (`/`) is your projects control center**: see projects, create them, filter by project, and see project-level streaks and activity. |
| **Curriculum** | The habit or arena | Where your **mastery target** lives (often **~1000 hours**) and where **sessions** attach. Progress % and hours roll up here and into the parent project. |
| **Item** | Roadmap row | Concrete work: papers, drills, loops. Items come in **one-time** and **daily** forms (presence or time-target). Completion is **manual** (one-shot or daily presence) or **automatic** (daily time target). |

**Project > Curriculum > Item** is the spine: if you’re “working every day” but one project never gets heatmap color, or one curriculum inside a project is flat, the app is designed to make that visible—not to average it away.

---

## Data-driven insight at every level

The app is built so you can spot **slacking or blind spots** without hand-waving:

- **Project (dashboard `/`)**  
  Per-project **streak** (consecutive days with any session in that project), **today** minutes, **365-day heatmap** (scoped when you filter), and a **curricula list** for the selected project. You land here first so you can’t ignore whole themes.

- **Curriculum (`/curriculums/<id>`)**  
  Pace (**hours per day you actually logged** in the last window, using **active days**, not blank calendar days), projected completion vs target date, per-item time, activity heatmap, and recent sessions—scoped to that curriculum.

- **Insights (`/insights`)**  
  Filter **by project**, then **by curriculum**. Daily and weekly charts and the mastery table respect that scope so you can compare “this project vs that” and drill to a single curriculum when you need to.

- **Curriculums index (`/curriculums`)**  
  Everything listed **grouped by project**—good for design and bulk navigation. “View project” goes to the **project detail** page for that bucket; the **projects list** itself lives on the dashboard, not on a duplicate `/projects` list route.

**Pace note:** velocity is **total hours in the trailing window ÷ distinct days with ≥1 session** in that scope (not “÷ 30” on the calendar). Idle days don’t dilute your average on days you actually showed up.

---

## Time logging (source of truth)

- **Sessions** are the ledger. Every log adds minutes to the **curriculum** and rolls up to the **project** when the curriculum belongs to one.
- If a curriculum has **daily time-target items**, you **tag the item** when logging time so per-item stats stay honest. (One-time and daily-presence items are checkmarks, not time ledgers.)
- **Manual entry** and the **stopwatch** on Log Time both write the same session type.
- Archiving structure doesn’t erase history until you delete sessions.

**Time** answers “how much did I invest?” **Checkboxes** answer “did I close the loop I care about?”—especially for **daily** habits.

### Daily items: presence vs time target

- **Presence (manual):** You tap the circle to mark “done today.” Resets each calendar day.
- **Time target (automatic):** You set **minutes required today on that item**. The checkmark turns on when **today’s sessions tagged to that item** sum to **≥ that target** (manual log or timer). You cannot manually toggle the check; log time to complete.

One-time items stay **manual** complete only.

---

## A lesson in humility: what 1000 hours really is

People throw around “10,000 hours” or even “1,000 hours” as if they’re ticket prices. They’re not. They’re **life**.

Rough orders of magnitude:

- **1 hour/day**, every single day → 1,000 hours is almost **three years**.
- **2 hours/day** → still well over a **year** of never missing.
- **One serious 3-hour block on weekdays only** → on the order of **a year and a half**.

That’s assuming the hours are **deliberate**—not half-distracted scrolling, not “being in the room.” A thousand *good* hours is a career’s worth of side attention for most people.

The app’s job is to make that **visible**: bars that move when you log, heatmaps that don’t care about your intentions, and scoped insights so you see **which project or curriculum you’re starving**.

If you use it honestly, it will feel slow. That’s the point. **Slowness is the shape of mastery.**

---

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_APP=app:create_app   # needed for `flask db …` CLI
flask db upgrade             # apply migrations (SQLite in instance/ by default)
python run.py                # http://127.0.0.1:5001
```

Configuration loads from `config.py` (and optional `.env`). By default the database is `instance/curriculum.db`. To use Neon locally, set `DATABASE_URL` before `flask db upgrade` / `python run.py`.

See `env.example` for variable names. **`DATABASE_URL`** switches the app to Postgres (Neon); if unset, SQLite is used.

---

## Deploy

This app is deployed on **Fly.io**.

Production uses **Gunicorn** and **Postgres** (recommended: [Neon](https://neon.tech)).

### Config reference (production)

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | Yes (prod) | Neon Postgres URI. |
| `SECRET_KEY` | Yes (prod) | Cookies / CSRF; must be stable across deploys. |
| `FLASK_APP` | For CLI / release | `app:create_app` for `flask db upgrade`. |
| `PUBLIC_BASE_URL` | Optional | Public app URL for absolute links / Open Graph previews. |

Local development uses SQLite unless `DATABASE_URL` is set.

### Redeploy after pulling new code

1. **Local:** `git pull`, then `export FLASK_APP=app:create_app` and `flask db upgrade` (uses your local DB or set `DATABASE_URL` for Neon).
2. **Fly:** deploy the latest image. If you added migrations, run `flask db upgrade` against the production database.
3. **Neon:** no change unless you rotate credentials.

---

## Stack

- Flask, SQLAlchemy, Flask-Migrate (Alembic), Flask-WTF, APScheduler (reminders), Flask-Mail (optional).
- Production: **Gunicorn**, **psycopg2-binary** (Postgres / Neon).

---

## License

See [LICENSE](LICENSE).
