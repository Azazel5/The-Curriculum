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
flask db upgrade             # apply migrations (SQLite in instance/ by default)
python run.py                # http://127.0.0.1:5001
```

Configuration loads from `config.py` (and optional `.env`). By default the database is `instance/curriculum.db`.

---

## Stack

- Flask, SQLAlchemy, Flask-Migrate (Alembic), Flask-WTF, APScheduler (reminders), Flask-Mail (optional).

---

## License

See [LICENSE](LICENSE).
