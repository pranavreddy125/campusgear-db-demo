# CampusGear database demo

A small EECS 581 progress demo: **HTML form → Python/Flask → SQL → SQLite**.
One page, one sample student (Alex Morgan), one Raspberry Pi Kit, one checkout.
The four tables are users, equipment, reservations, and loans. This web example
uses walk-in checkout, so its reservations table stays empty.

## Setup (Mac/Linux, Python 3.10+)

```bash
git clone https://github.com/pranavreddy125/campusgear-db-demo.git
cd campusgear-db-demo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app campusgear.web run --port 5810
```

On Windows, use `py -m venv .venv` and `.venv\Scripts\activate` in Command Prompt,
then the same `python` commands. If using Windows, also install `tzdata` with pip.

Open http://127.0.0.1:5810. Setup automatically creates
`instance/checkout-example.sqlite3` with Alex and an available kit.
Click **Check out** to save a loan and change the item status. Refreshing or
restarting preserves the checkout. Open that exact database file in DB Browser
and select Browse Data to see the rows.

This is a local-only example with a fixed borrower, not real login or staff
permissions. It does not implement reservations, returns, or the full application.
No database files or virtual environments are committed; each person creates
those locally. The original team repo is unchanged.

## Split the presentation (about 3 minutes)

### Pranav: page and request flow (1 minute)

1. Show the available Raspberry Pi Kit and borrower Alex Morgan.
2. Explain: “The page reads the item from our database.”
3. Click Check out. Show the status and due date changing.
4. Explain: “The form sends a POST request to Flask. Python checks availability,
   then calls our database code. The page reloads with the saved result.”
5. Point to the form in `campusgear/templates/checkout.html` and the two routes
   in `campusgear/web.py`: GET / displays data; POST /checkout performs checkout.

### Cam: SQL and saved records (1–2 minutes)

1. Open `instance/checkout-example.sqlite3` in DB Browser.
2. Explain users/equipment/reservations/loans and how IDs connect records.
3. Show the new loans row and equipment status `checked_out`.
4. In `campusgear/db.py`, show `checkout_example()`: check availability,
   INSERT the loan, UPDATE equipment. Both writes commit together or both roll back.
5. Explain that another checkout is rejected. Stop the server with Ctrl+C,
   restart it with the same command, and refresh to prove the data persists.

Suggested closing: “This demonstrates the complete connection from the page to
persistent storage. Authentication and full borrowing workflows are next.”

## Files to read in order

| File | Purpose |
| --- | --- |
| campusgear/templates/checkout.html | Plain HTML page and checkout form; no JavaScript |
| campusgear/web.py | Two Flask routes connecting the page to database functions |
| campusgear/db.py | Connection handling, SQL reads/writes, atomic checkout |
| campusgear/schema.sql | Four tables and their constraints |
| campusgear/demo.py | Separate terminal example covering all four record types |
| tests/ | Ten automated checks for storage and the web checkout |

A loan optionally references a reservation. This supports both reserved and
walk-in checkouts; linked borrower/item IDs must match. The team's original
architecture described reservation-only loans, while backlog Req 12 requires
walk-ins. Reflect this decision when integrating into the main project.
[Original team documents](https://github.com/540jmc17/PROJECT-3-GROUP18/tree/main/docs).

## Rehearse again without erasing data

Stop the server and start with a new unused database filename (Mac/Linux):

```bash
CAMPUSGEAR_DEMO_DB=instance/rehearsal-2.sqlite3 python -m flask --app campusgear.web run --port 5810
```

Open that new file in DB Browser. Each existing file keeps its own checkout.
Use another unused name each time you want a fresh run.

## Verification

With the virtual environment active:

```bash
python -m unittest discover -s tests -v
python -m campusgear.demo
```

Tests check references, uniqueness, dates, persistence, duplicate requests, and
rollback when a checkout write fails. The terminal demo creates a separate
`instance/demo-....sqlite3` with a reservation-based loan and a walk-in loan.
Database initialization preserves data but is not a schema migration tool.
