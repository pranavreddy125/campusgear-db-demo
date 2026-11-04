"""Req 7 preview checks. Codex for team review, revised 2026-11-04.
Checks visible role options and invalid-role fallback without modifying data.
"""
import unittest
from campusgear.web import create_app


class RoleDisplayTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

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
