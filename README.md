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
| **Item** | Roadmap row | Concrete work: papers, drills, loops. You log time on the curriculum and **tag the item** when the curriculum has items—so you can see **where time actually went**. Completion is **manual** (one-shot or daily reset). |

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
- If a curriculum has roadmap items, you **tag the item** so per-item stats and views stay honest.
- **Manual entry** and the **stopwatch** on Log Time both write the same session type.
- Archiving structure doesn’t erase history until you delete sessions.

**Time** answers “how much did I invest?” **Checkboxes** answer “did I close the loop I care about?”—especially for **daily** habits.

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

## Deploy on Render + Neon (free tier)

Production uses **Gunicorn** and **Postgres** (recommended: [Neon](https://neon.tech)). Render sets `RENDER` in the environment; the app then loads `ProductionConfig` (see `config.py` + `app/__init__.py`).

### A. Neon (database) — run in browser

1. Create a Neon account and a **project**.
2. Create a **branch** (default `main` is fine) and copy the **connection string** for `psql` or ORMs. It should look like  
   `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require`  
   If Neon shows `postgres://`, that is fine — the app normalizes it to `postgresql://`.

**Where:** Neon dashboard only (no terminal required for DB creation).

---

### B. GitHub (code) — run on your machine

```bash
git add -A
git commit -m "Prepare Render + Neon deploy"
git push origin main   # or your default branch
```

**Where:** your laptop, in the repo folder.

---

### C. Render (host) — mostly browser; one Release Command

1. [Render](https://render.com) → **New +** → **Web Service** → connect the GitHub repo.
2. **Settings:**
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn --bind 0.0.0.0:$PORT wsgi:app`
   - **Instance type:** Free (cold starts are normal on free tier)

3. **Environment** (Render → Environment → add variables):

   | Key | Value |
   |-----|--------|
   | `DATABASE_URL` | Paste Neon’s connection string (with `sslmode=require` if Neon docs say so). |
   | `SECRET_KEY` | Long random string (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"` on your machine). |
   | `FLASK_APP` | `app:create_app` |

   Optional (email reminders): `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` — same as local `config.py`.

4. **Release command** (migrations on every deploy — Render dashboard → *Settings* → *Build & Deploy* → *Release Command*):

   ```bash
   flask db upgrade
   ```

   Render runs this with the same env as the service, so `DATABASE_URL` and `FLASK_APP` must be set **before** the first successful release.

**Where:** Render dashboard + copy-paste commands above.

---

### D. First deploy order

1. Add env vars on Render (`DATABASE_URL`, `SECRET_KEY`, `FLASK_APP`).
2. Save; let the **first build** finish.
3. If the app starts before migrations ran, open **Manual Deploy** → **Clear build cache & deploy** after setting **Release Command** to `flask db upgrade`, or run migrations once from **Render Shell** (paid) / local against Neon:

**One-time migrations from your laptop** (if Release Command is not available on free tier — check Render’s UI; many plans include it):

```bash
export FLASK_APP=app:create_app
export DATABASE_URL='postgresql://...your-neon-url...'
pip install -r requirements.txt
flask db upgrade
```

**Where:** your laptop terminal (same `DATABASE_URL` as Render).

---

### E. After deploy

- Open the Render **URL** (e.g. `https://your-service.onrender.com`).
- Free web services **spin down** after idle; the first request may take ~30s.
- **Backups:** rely on Neon’s retention for important data; export periodically if you outgrow free tier.

---

### Config reference (production)

| Variable | Required | Notes |
|----------|----------|--------|
| `RENDER` | Auto | Set by Render; selects `ProductionConfig`. |
| `DATABASE_URL` | Yes (prod) | Neon Postgres URI. |
| `SECRET_KEY` | Yes (prod) | Cookies / CSRF; must be stable across deploys. |
| `FLASK_APP` | For CLI / Release | `app:create_app` for `flask db upgrade`. |

Local development ignores `RENDER` and uses SQLite unless `DATABASE_URL` is set.

---

## Stack

- Flask, SQLAlchemy, Flask-Migrate (Alembic), Flask-WTF, APScheduler (reminders), Flask-Mail (optional).
- Production: **Gunicorn**, **psycopg2-binary** (Postgres / Neon).

---

## License

See [LICENSE](LICENSE).
