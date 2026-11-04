"""Req 7 display preview, without login.

Programmer: Codex for team review. Revised: 2026-11-04.
Input: optional student/staff query parameter. Output: matching options.
Unknown roles default to student. No database writes or authorization here.
"""
from flask import Flask, render_template, request


def create_app():
    app = Flask(__name__)

    @app.get('/')
    def index():
        # Replace the selector with the authenticated user role during integration.
        role = request.args.get('role', 'student')
        if role not in ('student', 'staff'):
            role = 'student'
        return render_template('roles.html', role=role)

    return app
