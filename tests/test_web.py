"""Check the role preview and its SQLite integration."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from campusgear.db import insert_record, transaction
from campusgear.web import create_app


class RoleDisplayTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.database_path = Path(temp.name) / 'campusgear.sqlite3'
        self.client = create_app(self.database_path).test_client()

    def test_saved_equipment_is_displayed_after_restart(self):
        self.assertIn(b'No equipment has been saved yet.', self.client.get('/').data)
        with transaction(self.database_path) as connection:
            insert_record(connection, 'equipment', asset_id='KU-003', name='Camera',
                          category='Photography', description='Camera kit', status='maintenance')

        restarted_client = create_app(self.database_path).test_client()
        self.assertIn(b'Camera (KU-003)', restarted_client.get('/').data)

    def test_student_options(self):
        page = self.client.get('/?role=student')
        self.assertEqual(page.status_code, 200)
        self.assertIn(b'Reserve equipment', page.data)
        self.assertIn(b'My reservations and loans', page.data)
        self.assertNotIn(b'Add equipment', page.data)

    def test_staff_options(self):
        page = self.client.get('/?role=staff')
        self.assertIn(b'Add equipment', page.data)
        self.assertIn(b'Manage equipment', page.data)
        self.assertNotIn(b'Reserve equipment', page.data)

    def test_invalid_role_defaults_to_student(self):
        self.assertIn(b'Student options', self.client.get('/?role=admin').data)


if __name__ == '__main__':
    unittest.main()
