"""Req 1 regression checks for persistence and database integrity.

Programmer: Codex, for team review. Created/revised: 2026-11-03.
Preconditions: Python 3. Postconditions: temporary databases removed.
Errors: unittest reports failed acceptance checks with nonzero exit status.
"""

from pathlib import Path
import sqlite3
import tempfile
import unittest

from campusgear.db import initialize, transaction, insert_record, get_record, list_equipment
from campusgear.demo import seed


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'test.sqlite3'
        seed(self.path)

    def test_equipment_registration_and_catalog(self):
        with transaction(self.path) as connection:
            item_id = insert_record(connection, 'equipment', asset_id='KU-004',
                                    name='Camera', category='Photography', description='Camera kit')
        with transaction(self.path) as connection:
            self.assertEqual(len(list_equipment(connection)), 4)
            available = list_equipment(connection, available_only=True)
            self.assertEqual([item['asset_id'] for item in available], ['KU-003', 'KU-004'])
            self.assertEqual(available[1]['id'], item_id)
            self.assertEqual(available[1]['name'], 'Camera')
            self.assertEqual(available[1]['status'], 'available')

    def test_reinitialize_preserves_all_records(self):
        initialize(self.path)
        with transaction(self.path) as connection:
            for table in ('users', 'equipment', 'reservations', 'loans'):
                self.assertIsNotNone(get_record(connection, table, 1))

    def test_invalid_relationships(self):
        # Check each relationship, including mismatched reservation ownership.
        cases = [
            ('reservations', dict(user_id=999, equipment_id=1,
                                  pickup_date='2026-11-03', return_date='2026-11-10')),
            ('reservations', dict(user_id=1, equipment_id=999,
                                  pickup_date='2026-11-03', return_date='2026-11-10')),
            ('loans', dict(user_id=999, equipment_id=1)),
            ('loans', dict(user_id=1, equipment_id=999)),
            ('loans', dict(user_id=1, equipment_id=1, reservation_id=999)),
            ('loans', dict(user_id=2, equipment_id=1, reservation_id=1)),
            ('loans', dict(user_id=1, equipment_id=2, reservation_id=1)),
        ]
        # Remove the seeded linked loan so uniqueness cannot mask FK failures.
        with transaction(self.path) as connection:
            connection.execute('DELETE FROM loans WHERE reservation_id = 1')
        for table, fields in cases:
            with self.subTest(table=table, fields=fields):
                if table == 'loans':
                    fields.update(checkout_date='2026-11-03', due_date='2026-11-10')
                with self.assertRaisesRegex(sqlite3.IntegrityError, 'FOREIGN KEY'):
                    with transaction(self.path) as connection:
                        insert_record(connection, table, **fields)

    def test_unique_asset_email_and_reservation_loan(self):
        statements = [
            "UPDATE equipment SET asset_id = 'KU-001' WHERE id = 2",
            "UPDATE users SET email = 'ALEX.MORGAN@example.invalid' WHERE id = 2",
            "UPDATE loans SET reservation_id = 1, equipment_id = 1 WHERE id = 2",
        ]
        for sql in statements:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                with transaction(self.path) as connection:
                    connection.execute(sql)

    def test_dates_status_and_required_values(self):
        statements = [
            "UPDATE reservations SET return_date = pickup_date",
            "UPDATE reservations SET pickup_date = '2026-02-30'",
            "UPDATE loans SET due_date = 'bad-date'",
            "UPDATE loans SET due_date = checkout_date",
            "UPDATE loans SET status = 'returned'",
            "UPDATE users SET role = 'admin'",
            "UPDATE equipment SET status = 'unknown'",
            "UPDATE equipment SET name = ''",
            "UPDATE users SET password_hash = NULL",
        ]
        for sql in statements:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                with transaction(self.path) as connection:
                    connection.execute(sql)

    def test_return_and_history(self):
        with transaction(self.path) as connection:
            connection.execute("UPDATE loans SET status = 'returned', "
                               "actual_return_date = '2026-11-05' WHERE id = 1")
        with transaction(self.path) as connection:
            self.assertEqual(get_record(connection, 'loans', 1)['status'], 'returned')
        for table in ('users', 'equipment', 'reservations'):
            with self.subTest(table=table), self.assertRaises(sqlite3.IntegrityError):
                with transaction(self.path) as connection:
                    connection.execute(f'DELETE FROM {table} WHERE id = 1')

    def test_transaction_rolls_back_all_changes(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with transaction(self.path) as connection:
                connection.execute("UPDATE equipment SET name = 'Changed' WHERE id = 1")
                connection.execute("UPDATE users SET role = 'invalid' WHERE id = 1")
        with transaction(self.path) as connection:
            self.assertEqual(get_record(connection, 'equipment', 1)['name'], 'Raspberry Pi Kit')

    def test_allowlisted_identifiers_and_parameterized_values(self):
        with transaction(self.path) as connection:
            with self.assertRaises(ValueError):
                get_record(connection, 'users; DROP TABLE users', 1)
            self.assertIsNone(get_record(connection, 'users', '1 OR 1=1'))
            user_id = insert_record(connection, 'users', name="O'Brien", email='other@example.invalid',
                                    password_hash='!disabled', role='student')
            self.assertEqual(get_record(connection, 'users', user_id)['name'], "O'Brien")


if __name__ == '__main__':
    unittest.main()
