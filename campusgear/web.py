"""Role display preview backed by the shared CampusGear database.

Programmer: Codex for team review. Revised: 2026-11-04.
Input: optional student/staff query parameter. Output: matching options.
Unknown roles default to student. Reservations use the local demo student.
"""
from datetime import date
import sqlite3

from flask import Flask, abort, redirect, render_template, request, url_for

from .db import DEFAULT_PATH, get_record, initialize, insert_record, list_equipment, transaction
from .demo import DEMO_STUDENT_EMAIL

EQUIPMENT_STATUSES = ('available', 'reserved', 'checked_out', 'maintenance')


def create_app(database_path=DEFAULT_PATH):
    app = Flask(__name__)
    app.config['DATABASE'] = database_path
    initialize(app.config['DATABASE'])

    def page(role, error=None):
        with transaction(app.config['DATABASE']) as connection:
            equipment = list_equipment(connection)
        return render_template('roles.html', role=role, equipment=equipment,
                               available=[item for item in equipment if item['status'] == 'available'],
                               equipment_statuses=EQUIPMENT_STATUSES, error=error)

    @app.get('/')
    def index():
        # Replace the selector with the authenticated user role during integration.
        role = request.args.get('role', 'student')
        return page('staff' if role == 'staff' else 'student')

    @app.post('/reserve')
    def reserve():
        equipment_id = request.form.get('equipment_id', type=int)
        if equipment_id is None or not 0 < equipment_id <= 2**63 - 1:
            return page('student', 'Choose an equipment item.'), 400
        try:
            pickup = date.fromisoformat(request.form.get('pickup_date', ''))
            dropoff = date.fromisoformat(request.form.get('return_date', ''))
        except ValueError:
            return page('student', 'Enter valid pickup and return dates.'), 400
        if dropoff <= pickup:
            return page('student', 'Return date must follow pickup date.'), 400

        with transaction(app.config['DATABASE']) as connection:
            # Serialize the availability check and insert for concurrent submissions.
            connection.execute('BEGIN IMMEDIATE')
            student = connection.execute(
                "SELECT id FROM users WHERE email = ? AND role = 'student'",
                (DEMO_STUDENT_EMAIL,),
            ).fetchone()
            item = get_record(connection, 'equipment', equipment_id)
            conflict = connection.execute(
                "SELECT 1 FROM reservations WHERE equipment_id = ? "
                "AND status IN ('reserved', 'checked_out') AND pickup_date < ? AND return_date > ?",
                (equipment_id, dropoff.isoformat(), pickup.isoformat()),
            ).fetchone()
            if student is None:
                error = 'Start the preview with the sample database to reserve equipment.'
            elif item is None or item['status'] != 'available' or conflict:
                error = 'That equipment is unavailable for the selected dates.'
            else:
                insert_record(connection, 'reservations', user_id=student['id'],
                              equipment_id=equipment_id, pickup_date=pickup.isoformat(),
                              return_date=dropoff.isoformat())
                error = None

        if error:
            return page('student', error), 409
        return redirect(url_for('index', role='student', reserved=1, _anchor='role-options'), code=303)

    @app.post('/equipment')
    def add_equipment():
        fields = {field: request.form.get(field, '').strip()
                  for field in ('asset_id', 'name', 'category', 'description')}
        if not all(fields.values()):
            return page('staff', 'Enter an asset ID, name, category, and description.'), 400

        try:
            with transaction(app.config['DATABASE']) as connection:
                insert_record(connection, 'equipment', **fields)
        except sqlite3.IntegrityError as error:
            if str(error) != 'UNIQUE constraint failed: equipment.asset_id':
                raise
            return page('staff', 'That asset ID is already in use.'), 409
        return redirect(url_for('index', role='staff', added=1, _anchor='role-options'), code=303)

    @app.post('/equipment/<int:equipment_id>')
    def update_equipment(equipment_id):
        if not 0 < equipment_id <= 2**63 - 1:
            abort(404)
        condition = request.form.get('condition', '').strip()
        status = request.form.get('status')
        if not condition or status not in EQUIPMENT_STATUSES:
            return page('staff', 'Enter a condition and choose a valid status.'), 400

        with transaction(app.config['DATABASE']) as connection:
            updated = connection.execute(
                "UPDATE equipment SET condition = ?, status = ? WHERE id = ? "
                "AND (? <> 'available' OR NOT EXISTS (SELECT 1 FROM loans "
                "WHERE equipment_id = equipment.id AND status = 'checked_out'))",
                (condition, status, equipment_id, status),
            ).rowcount
            if not updated and get_record(connection, 'equipment', equipment_id) is None:
                abort(404)
        if not updated:
            return page('staff', 'An item with an active loan cannot be marked available.'), 409
        return redirect(url_for('index', role='staff', updated=1, _anchor='manage-equipment'), code=303)

    return app
