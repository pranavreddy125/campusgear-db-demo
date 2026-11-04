"""Minimal local checkout page: browser -> Flask -> db.py -> SQLite.

Programmer: Codex, for Pranav/Cameren review. Created/revised: 2026-11-03.
Preconditions: Flask installed; writable dedicated web-example database.
Postconditions: GET displays saved data; POST saves one checkout then redirects.
Errors: unavailable checkout returns 409; database failures roll back.
Scope: fixed sample student, no login or production authorization.
"""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import os

from flask import Flask, redirect, render_template, url_for, request

from .db import DEFAULT_PATH, prepare_checkout_example, read_checkout_example, checkout_example, reset_checkout_example


def create_app(database_path=None):
    app = Flask(__name__)
    path = Path(database_path or os.environ.get(
        'CAMPUSGEAR_DEMO_DB', DEFAULT_PATH.parent / 'checkout-example.sqlite3'))
    prepare_checkout_example(path)

    def selected_role():
        # Temporary display choice only; real login will supply the role later.
        role = request.values.get('role', 'student')
        return role if role in ('student', 'staff') else 'student'

    def page(error=None):
        student, item, loan = read_checkout_example(path)
        return render_template('checkout.html', student=student, item=item, loan=loan, error=error, role=selected_role())

    @app.get('/')
    def index():
        """Read SQLite and show the page; never change data on refresh."""
        return page()

    @app.post('/checkout')
    def checkout():
        """Receive the form, save a seven-day checkout, then reload the page."""
        today = datetime.now(ZoneInfo('America/Chicago')).date()
        try:
            checkout_example(path, today.isoformat(), (today + timedelta(days=7)).isoformat())
        except ValueError as error:
            return page(str(error)), 409
        return redirect(url_for('index', role=selected_role()), code=303)

    @app.post('/reset')
    def reset():
        """Clear this sample checkout so the presentation can be repeated."""
        reset_checkout_example(path)
        return redirect(url_for('index', role=selected_role()), code=303)

    return app
