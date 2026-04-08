# The Curriculum

A small Flask app for tracking **deliberate practice** without fooling yourself. It’s built for people who have more ambition than consistency and who want the numbers to tell the truth.

---

## Why this exists

Most of us know *what* we want to get good at; fewer of us can point to **how many honest hours** we’ve put in. This app separates **big goals** from **day-to-day work**, and ties progress to **logged time**—not vibes. The roadmap checkboxes are a separate, honest signal: *I did what I meant to do today / for this task*, including a **daily** mode that resets each calendar day while **keeping every minute you’ve ever logged** on that row.

It’s also a humility tool. A thousand hours sounds abstract until you try to **earn** them in real weeks.

---

## How the pieces fit together

Think in three layers:

| Layer | What it is | Role |
|--------|------------|------|
| **Project** | A theme or North Star | Groups related pursuits (e.g. “Research skills,” “Interview prep”). Optional but useful when one life area has several curricula. |
| **Curriculum** | The main habit or arena | This is where your **mastery target** lives (default often **1000 hours**)—the bar you’re trying to fill with real sessions. Progress % and “hours logged” roll up here. |
| **Item** | A concrete row on the roadmap | Papers to read, skills to drill, loops to close. You **log time against the curriculum** and **tag sessions to an item** when the curriculum has items—so hours attach to something specific. |

**Goals vs. items**

- The **curriculum’s mastery hours** are the big, humbling number: how much *focused* work you’re claiming it takes to matter here.
- **Items** are the checklist you actually touch day to day: deadlines, descriptions, and (for **daily** rows) a fresh “done for today” checkbox every morning while **cumulative hours on that item** keep growing forever.

Nothing magic crosses an item off: you **check it** when you’re satisfied. The clock doesn’t lie; the check is your judgment call.

---

## Time logging (the source of truth)

- **Sessions** are the ledger. Every log adds minutes to the **curriculum** (and to the **project**, if linked).
- If a curriculum has roadmap items, you **tag the item** so per-item and heatmap views reflect where the time went.
- **Manual entry** and a **stopwatch** on the Log Time page both write the same kind of session.
- Deleting or archiving structure doesn’t rewrite history: old sessions stay until you delete them.

So: **time answers “how much have I actually invested?”** The **checkbox** answers “did I close the loop I care about?”—especially meaningful for **daily** habits where consistency beats intensity.

---

## A lesson in humility: what 1000 hours really is

People throw around “10,000 hours” or even “1,000 hours” as if they’re ticket prices. They’re not. They’re **life**.

Rough orders of magnitude:

- **1 hour/day**, every single day → 1,000 hours is almost **three years**.
- **2 hours/day** → still well over a **year** of never missing.
- **One serious 3-hour block on weekdays only** → on the order of **a year and a half**.

That’s assuming the hours are **deliberate**—not half-distracted scrolling, not “being in the room.” A thousand *good* hours is a career’s worth of side attention for most people. Ten thousand is a lifetime theme, not a semester project.

The app’s job is to make that **visible**: a bar that moves when you log, a heatmap that doesn’t care about your intentions, and a number that goes up only when you admit what you did with the clock.

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
