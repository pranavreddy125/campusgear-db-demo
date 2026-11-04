"""Local checkout integration tests. Programmer: Codex for team review.
Created/revised: 2026-11-03. Uses temporary SQLite files; leaves user data alone.
Checks HTTP responses, atomic storage, duplicate requests, and app restart.
Failures are reported by unittest with a nonzero exit status.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest

from campusgear.db import transaction, checkout_example
from campusgear.web import create_app


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'checkout.sqlite3'
        self.app = create_app(self.path)
        self.app.testing = True
        self.client = self.app.test_client()

    def test_checkout_persists_after_restart(self):
        page = self.client.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Available', page.data)
        self.assertNotIn(b'password_hash', page.data)
        self.assertEqual(self.client.get('/checkout').status_code, 405)
        self.assertEqual(self.client.post('/checkout').status_code, 303)
        restarted = create_app(self.path).test_client()
        page = restarted.get('/')
        self.assertIn(b'Checked out to Alex Morgan.', page.data)
        with transaction(self.path) as connection:
            loan = connection.execute('SELECT * FROM loans').fetchone()
            self.assertEqual((loan['user_id'], loan['equipment_id']), (1, 1))
            self.assertIsNone(loan['reservation_id'])
            self.assertEqual(connection.execute(
                'SELECT julianday(due_date)-julianday(checkout_date) FROM loans'
            ).fetchone()[0], 7)
            self.assertEqual(connection.execute('SELECT status FROM equipment').fetchone()[0],
                             'checked_out')

    def test_role_preview_and_preservation(self):
        student = self.client.get('/?role=student').data
        self.assertIn(b'Reserve equipment', student)
        self.assertNotIn(b'Add equipment', student)
        staff = self.client.get('/?role=staff').data
        self.assertIn(b'Add equipment', staff)
        self.assertNotIn(b'Reserve equipment', staff)
        self.assertIn(b'Student options', self.client.get('/?role=admin').data)
        for action in ('/checkout', '/reset'):
            response = self.client.post(action, data={'role': 'staff'}, follow_redirects=True)
            self.assertIn(b'Staff options', response.data)

    def test_reset_allows_another_checkout(self):
        self.assertEqual(self.client.get('/reset').status_code, 405)
        self.client.post('/checkout')
        self.assertEqual(self.client.post('/reset').status_code, 303)
        self.assertIn(b'Available', self.client.get('/').data)
        with transaction(self.path) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM loans').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT count(*) FROM users').fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT count(*) FROM equipment').fetchone()[0], 1)
        self.assertEqual(self.client.post('/reset').status_code, 303)
        self.assertEqual(self.client.post('/checkout').status_code, 303)

    def test_double_click_creates_only_one_loan(self):
        def click(_):
            with self.app.test_client() as client:
                return client.post('/checkout').status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(click, range(2))), [303, 409])
        with transaction(self.path) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM loans').fetchone()[0], 1)

    def test_failed_equipment_update_rolls_back_loan(self):
        # Force the second write to fail, proving the first cannot be left behind.
        with transaction(self.path) as connection:
            connection.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON equipment "
                               "BEGIN SELECT RAISE(ABORT, 'forced test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            checkout_example(self.path, '2026-11-03', '2026-11-10')
        with transaction(self.path) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM loans').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT status FROM equipment').fetchone()[0],
                             'available')


if __name__ == '__main__':
    unittest.main()
