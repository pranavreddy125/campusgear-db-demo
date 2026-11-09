"""Role display preview backed by the shared CampusGear database.

Programmer: Codex for team review. Revised: 2026-11-04.
Input: optional student/staff query parameter. Output: matching options.
Unknown roles default to student. No database writes or authorization here.
"""
from flask import Flask, render_template, request

from .db import DEFAULT_PATH, initialize, list_equipment, transaction


def create_app(database_path=DEFAULT_PATH):
    app = Flask(__name__)
    app.config['DATABASE'] = database_path
    initialize(app.config['DATABASE'])

    @app.get('/')
    def index():
        # Replace the selector with the authenticated user role during integration.
        role = request.args.get('role', 'student')
        if role not in ('student', 'staff'):
            role = 'student'
        with transaction(app.config['DATABASE']) as connection:
            equipment = list_equipment(connection)
        return render_template('roles.html', role=role, equipment=equipment)

    return app
