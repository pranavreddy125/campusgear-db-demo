# CampusGear — Pranav/Cam, Requirements 1 and 7

`main` contains our database setup and student/staff display preview.
The older checkout/reset proof of concept is on branch `poc-checkout-demo`.

## Cam: run it (Mac/Linux, Python 3.10+)

```bash
git clone https://github.com/pranavreddy125/campusgear-db-demo.git
cd campusgear-db-demo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m campusgear.demo
python -m flask --app campusgear.web run --port 5810
```

If already cloned, run `git switch main` and `git pull` first.
On Windows, use `py -m venv .venv` and `.venv\Scripts\activate` in Command Prompt.

- **Req 1:** Flask initializes `instance/campusgear.sqlite3` on startup and reads
  saved equipment on the preview page. The application database starts empty and
  keeps its records across restarts. The terminal demo uses a separate sample
  database to verify storage for all four record types and foreign key checks.
- **Req 7:** open http://127.0.0.1:5810, select Student/Staff, and click Show view.
  Options are placeholders. No login or permissions yet; integrate into Jake/John’s
  UI later and replace the selector with the real account role for the release.

## Files

- `campusgear/schema.sql`: users, equipment, reservations, loans and their rules.
- `campusgear/db.py`: shared connection, initialization, save/read, equipment list.
- `campusgear/demo.py`: sample records and persistence check.
- `campusgear/web.py` + `templates/roles.html`: role-specific display.

Run tests: `python -m unittest discover -s tests -v`.

For the TA: Pranav shows role switching and the request flow; Cam shows the four
DB tables, linked IDs, persistence, and invalid-reference check.

## What remains

Combine with the team UI, connect equipment form/catalog handlers, then integrate
real login/permissions for Sprint 1. We are not implementing equipment pages,
checkout/reset workflows, or login in this branch. Sample loans remain for Req 1.

Karim/Ahmed’s database interface is in [EQUIPMENT_INTEGRATION.md](EQUIPMENT_INTEGRATION.md).
No request to Jake/John is needed yet; their UI files will be needed at integration.
Database files and virtual environments stay local and are ignored by Git.
