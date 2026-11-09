"""Check the role preview and its SQLite integration."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from campusgear.db import insert_record, transaction
from campusgear.demo import seed
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

    def test_staff_can_add_and_manage_equipment(self):
        fields = {'asset_id': 'KU-004', 'name': 'Tripod', 'category': 'Photography',
                  'description': 'Camera tripod'}
        response = self.client.post('/equipment', data=fields, follow_redirects=True)
        self.assertIn(b'Equipment added.', response.data)
        self.assertEqual(self.client.post('/equipment', data=fields).status_code, 409)
        self.assertIn(b'<option value="1">Tripod (KU-004)</option>', self.client.get('/').data)

        response = self.client.post('/equipment/1', data={'condition': 'Needs repair',
                                                         'status': 'maintenance'}, follow_redirects=True)
        self.assertIn(b'Equipment updated.', response.data)
        self.assertIn(b'No equipment is available to reserve.', self.client.get('/').data)
        with transaction(self.database_path) as connection:
            row = connection.execute('SELECT condition, status FROM equipment').fetchone()
        self.assertEqual(tuple(row), ('Needs repair', 'maintenance'))

    def test_staff_cannot_mark_an_item_on_loan_available(self):
        seed(self.database_path)
        response = self.client.post('/equipment/1', data={'condition': 'Good', 'status': 'available'})
        self.assertEqual(response.status_code, 409)

    def test_student_can_reserve_available_equipment(self):
        seed(self.database_path)
        fields = {'equipment_id': 3, 'pickup_date': '2027-01-10', 'return_date': '2027-01-12'}
        response = self.client.post('/reserve', data=fields, follow_redirects=True)
        self.assertIn(b'Reservation saved.', response.data)
        self.assertEqual(self.client.post('/reserve', data=fields).status_code, 409)
        self.assertEqual(self.client.post('/reserve', data=dict(fields, equipment_id=2)).status_code, 409)
        self.assertEqual(self.client.post('/reserve', data=dict(fields, return_date='2027-01-09')).status_code, 400)
        with transaction(self.database_path) as connection:
            rows = connection.execute('SELECT user_id, pickup_date, return_date FROM reservations '
                                      'WHERE equipment_id = 3').fetchall()
        self.assertEqual([tuple(row) for row in rows], [(1, '2027-01-10', '2027-01-12')])

    def test_invalid_role_defaults_to_student(self):
        self.assertIn(b'Student options', self.client.get('/?role=admin').data)


if __name__ == '__main__':
    unittest.main()
