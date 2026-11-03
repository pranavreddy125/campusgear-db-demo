"""Shared SQLite access for Req 1; usable by a future Flask backend.

Programmer: Codex, for Pranav/Cameren review.
Created/revised: 2026-11-03 (initial implementation).
Preconditions: writable database path; callers supply trusted table/field names
from the allowed schema and password hashes produced by the login component.
Postconditions: successful transaction blocks commit; failed blocks roll back.
Errors: ValueError for unknown names; sqlite3 errors for invalid data or I/O.
This module stores records; authorization and checkout workflows belong to the
business layer, not to these low-level functions.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3


DEFAULT_PATH = Path(__file__).resolve().parent.parent / 'instance' / 'campusgear.sqlite3'
FIELDS = {
    'users': {'name', 'email', 'password_hash', 'role'},
    'equipment': {'asset_id', 'name', 'category', 'description', 'condition', 'status'},
    'reservations': {'user_id', 'equipment_id', 'pickup_date', 'return_date', 'status'},
    'loans': {'user_id', 'equipment_id', 'reservation_id', 'checkout_date',
              'due_date', 'actual_return_date', 'status'},
}


@contextmanager
def transaction(path=DEFAULT_PATH):
    """Open a connection, enforce references, commit/rollback, and always close."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path=DEFAULT_PATH):
    """Create missing tables without deleting existing records."""
    with transaction(path) as connection:
        connection.executescript(Path(__file__).with_name('schema.sql').read_text())


def _validate(table, fields=()):
    if table not in FIELDS or not set(fields).issubset(FIELDS[table]):
        raise ValueError('Unknown table or field')


def insert_record(connection, table, **fields):
    """Insert one record; return its ID. Caller owns the transaction boundary."""
    _validate(table, fields)
    if not fields:
        raise ValueError('At least one field is required')
    # Only allowlisted identifiers enter SQL; all user values use placeholders.
    columns = ', '.join(fields)
    placeholders = ', '.join('?' for _ in fields)
    cursor = connection.execute(
        f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', tuple(fields.values()))
    return cursor.lastrowid


def get_record(connection, table, record_id):
    """Retrieve one record as a dictionary, or None if its ID does not exist.

    Internal access only: callers must authorize reads and avoid returning a
    user record's password_hash to a browser.
    """
    _validate(table)
    row = connection.execute(f'SELECT * FROM {table} WHERE id = ?', (record_id,)).fetchone()
    return dict(row) if row else None


def prepare_checkout_example(path):
    """Seed the dedicated web example once; preserve existing checkouts."""
    initialize(path)
    with transaction(path) as connection:
        connection.execute('BEGIN IMMEDIATE')
        if connection.execute('SELECT id FROM users LIMIT 1').fetchone() is None:
            insert_record(connection, 'users', name='Alex Morgan',
                          email='alex.morgan@example.invalid',
                          password_hash='!login-disabled', role='student')
            insert_record(connection, 'equipment', asset_id='KU-001',
                          name='Raspberry Pi Kit', category='Electronics',
                          description='Raspberry Pi with power supply, case, and cables.')


def read_checkout_example(path):
    """Read the fixed student, item, and any saved loan for the page."""
    with transaction(path) as connection:
        student = connection.execute('SELECT id, name FROM users WHERE id = 1').fetchone()
        item = get_record(connection, 'equipment', 1)
        loan = connection.execute(
            'SELECT * FROM loans WHERE equipment_id = 1 ORDER BY id DESC LIMIT 1'
        ).fetchone()
        return student, item, loan


def checkout_example(path, checkout_date, due_date):
    """Check out the example item atomically; reject a repeated checkout.

    Raises ValueError when unavailable and sqlite3 errors for invalid records.
    Fixed student/item IDs are for this isolated local example, not authorization.
    """
    with transaction(path) as connection:
        # Lock before reading so two clicks cannot both see an available item.
        connection.execute('BEGIN IMMEDIATE')
        item = get_record(connection, 'equipment', 1)
        if item is None or item['status'] != 'available':
            raise ValueError('This item is already checked out or unavailable.')

        # Both writes commit together. If either fails, neither is saved.
        connection.execute(
            'INSERT INTO loans (user_id, equipment_id, checkout_date, due_date) '
            'VALUES (?, ?, ?, ?)', (1, 1, checkout_date, due_date))
        connection.execute("UPDATE equipment SET status = 'checked_out' WHERE id = ?", (1,))
