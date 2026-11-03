

import argparse
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

from .db import DEFAULT_PATH, initialize, transaction, insert_record, get_record


def seed(path):
    """Save all four record types together, including a separate walk-in loan."""
    initialize(path)
    with transaction(path) as connection:
        student = insert_record(connection, 'users', name='Alex Morgan',
                                email='alex.morgan@example.invalid',
                                password_hash='!demo-login-disabled', role='student')
        insert_record(connection, 'users', name='Jordan Lee', email='jordan.lee@example.invalid',
                      password_hash='!demo-login-disabled', role='staff')
        item_ids = [insert_record(connection, 'equipment', asset_id=f'KU-{i:03d}',
                                 name=name, category='Lab gear', description=description,
                                 status='checked_out')
                    for i, (name, description) in enumerate((
                        ('Raspberry Pi Kit', 'Raspberry Pi with power supply, case, and cables.'),
                        ('Soldering Kit', 'Soldering iron with stand and basic accessories.')), 1)]
        reservation = insert_record(connection, 'reservations', user_id=student,
                                    equipment_id=item_ids[0], pickup_date='2026-11-03',
                                    return_date='2026-11-10', status='checked_out')
        for item, reservation_id in zip(item_ids, (reservation, None)):
            insert_record(connection, 'loans', user_id=student, equipment_id=item,
                          reservation_id=reservation_id, checkout_date='2026-11-03',
                          due_date='2026-11-10')


def verify(path):
    """Read committed records in a fresh process and exercise reference checks."""
    with transaction(path) as connection:
        counts = {table: connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                  for table in ('users', 'equipment', 'reservations', 'loans')}
        assert counts == {'users': 2, 'equipment': 2, 'reservations': 1, 'loans': 2}
        assert get_record(connection, 'users', 1)['role'] == 'student'
        assert get_record(connection, 'equipment', 1)['asset_id'] == 'KU-001'
        assert get_record(connection, 'reservations', 1)['user_id'] == 1
        assert get_record(connection, 'loans', 1)['reservation_id'] == 1
        assert get_record(connection, 'loans', 2)['reservation_id'] is None
        try:
            insert_record(connection, 'reservations', user_id=999999, equipment_id=1,
                          pickup_date='2026-11-04', return_date='2026-11-05')
        except sqlite3.IntegrityError:
            pass  # Expected: the referenced user does not exist.
        else:
            raise AssertionError('Invalid user relationship was accepted')
        assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    print(f'Database: {path.resolve()}')
    print('PASS: saved and retrieved all four record types')
    for table, count in counts.items():
        print(f'  {table}: {count} records')
    print('PASS: records remain after the writer closes (read in a new process)')
    print('PASS: reservation for nonexistent user rejected')
    print('PASS: reservation-based and walk-in loans stored')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path, help='Verify an existing demo database')
    args = parser.parse_args()
    if args.verify:
        verify(args.verify)
    else:
        path = DEFAULT_PATH.parent / f'demo-{uuid4().hex}.sqlite3'
        seed(path)
        # The writer's connections are closed before a new interpreter reads.
        subprocess.run([sys.executable, '-m', 'campusgear.demo', '--verify', str(path)],
                       check=True, cwd=Path(__file__).resolve().parent.parent)


if __name__ == '__main__':
    main()
