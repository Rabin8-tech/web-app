import os
os.environ['MYSQL_HOST'] = '127.0.0.1'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = 'rabin8866'
os.environ['MYSQL_DB'] = 'test_mydatabase'
os.environ['MYSQL_PORT'] = '3306'

from app import app, mysql  # Import after setting env variables

import pytest
from flask import session
import requests  # Needed for monkeypatching
import re

@pytest.fixture
def client():
    """
    Pytest fixture that configures the app for testing. It:
      - Disables CSRF protection.
      - Uses a dedicated test database.
      - Sets up (or resets) the users table.
      - Creates and yields a test client within an application context.
      - Drops the users table after testing.
    """
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['MYSQL_DB'] = 'test_mydatabase'  # Ensure this database exists and is accessible

    with app.app_context():
        # Ensure the connection is active.
        mysql.connection.ping()
        cursor = mysql.connection.cursor()
        # Drop any existing table and create a fresh one.
        cursor.execute("DROP TABLE IF EXISTS users;")
        mysql.connection.commit()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """)
        mysql.connection.commit()

        # Create the test client and yield it.
        with app.test_client() as client:
            yield client

        # Teardown: Drop the test table.
        mysql.connection.ping()
        cursor.execute("DROP TABLE IF EXISTS users;")
        mysql.connection.commit()

def test_register(client):
    """
    Test user registration:
      - Check that a registration attempt yields a page with a form.
      - Verify duplicate registrations are handled.
      - Verify that the password stored is hashed (and not plaintext).
    """
    # Submit the registration form.
    response = client.post(
        "/register",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )
    assert b"<form" in response.data and b"Email" in response.data

    # Verify the stored password is hashed
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT password FROM users WHERE email = %s", ("test@example.com",))
    result = cursor.fetchone()
    # The password should not equal the plaintext and should match bcrypt's pattern.
    assert result is not None
    stored_password = result['password']
    assert stored_password != "password123"
    # Check for bcrypt hash format (commonly starts with "$2b$" or "$2a$")
    assert re.match(r"^\$2[abxy]\$", stored_password)

    # Attempt duplicate registration.
    response = client.post(
        "/register",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )
    # Either a flash message "Email already registered" is rendered or the form is re-displayed.
    assert b"Email already registered" in response.data or b"<form" in response.data

def test_sql_injection_prevention(client):
    """
    Test that SQL injection is prevented by:
      - Attempting to register with a malicious email.
      - Ensuring that the email is stored as-is and no extra records are created.
    """
    malicious_email = "malicious@example.com' OR '1'='1"
    response = client.post(
        "/register",
        data=dict(email=malicious_email, password="password123"),
        follow_redirects=True
    )
    # The registration should succeed, storing the email exactly as provided.
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
    result = cursor.fetchone()
    # There should be exactly one record created.
    assert result['cnt'] == 1

    cursor.execute("SELECT email FROM users;")
    result = cursor.fetchone()
    # The stored email should match exactly the malicious string (i.e. no SQL injection happened).
    assert result['email'] == malicious_email.lower()


def test_login(client):
    """
    Test login functionality:
      - Successful login sets the session and redirects appropriately.
      - Login with an unregistered email does not set the session.
      - Login with an incorrect password does not set the session.
    """
    # Register the test user.
    client.post(
        "/register",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )

    # ------- Successful Login -------
    response = client.post(
        "/login",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )
    with client.session_transaction() as sess:
        assert sess.get("user_id") == "test@example.com"
    assert b"test@example.com" in response.data

    with client.session_transaction() as sess:
        sess.clear()

    # ------- Login Attempt with Unregistered Email -------
    response = client.post(
        "/login",
        data=dict(email="nosuchuser@example.com", password="password123"),
        follow_redirects=True
    )
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None
    assert b"<form" in response.data and b"Email" in response.data

    with client.session_transaction() as sess:
        sess.clear()

    # ------- Login Attempt with Incorrect Password -------
    response = client.post(
        "/login",
        data=dict(email="test@example.com", password="wrongpassword"),
        follow_redirects=True
    )
    with client.session_transaction() as sess:
        assert sess.get("user_id") is None
    assert b"<form" in response.data and b"Email" in response.data

def test_dashboard_access(client):
    """
    Test dashboard access:
      - When logged in, the dashboard should display user-specific content.
      - When not logged in, accessing the dashboard should redirect to the login page.
    """
    client.post(
        "/register",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )
    client.post(
        "/login",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )

    response = client.get("/dashboard", follow_redirects=True)
    assert b"test@example.com" in response.data

    with client.session_transaction() as sess:
        sess.clear()

    response = client.get("/dashboard", follow_redirects=True)
    assert b"<form" in response.data and b"Email" in response.data

def test_dashboard_openverse_search(client, monkeypatch):
    """
    Test the dashboard search functionality for Openverse integration:
      - After logging in, submit a search query.
      - Monkeypatch requests.get to return dummy responses for both images and audio.
      - Verify that the dummy search results are rendered on the dashboard.
    """
    class DummyResponse:
        def __init__(self, results, status_code=200):
            self._results = results
            self.status_code = status_code

        def json(self):
            return {"results": self._results}

    def dummy_get(url, headers):
        if "/images/" in url:
            return DummyResponse(results=[{"title": "dummy image"}])
        elif "/audio/" in url:
            return DummyResponse(results=[{"title": "dummy audio"}])
        return DummyResponse(results=[], status_code=404)

    monkeypatch.setattr("requests.get", dummy_get)

    client.post(
        "/register",
        data=dict(email="openverse@test.com", password="password123"),
        follow_redirects=True
    )
    client.post(
        "/login",
        data=dict(email="openverse@test.com", password="password123"),
        follow_redirects=True
    )

    response = client.post(
        "/dashboard",
        data=dict(query="nature"),
        follow_redirects=True
    )

    assert b"dummy image" in response.data
    assert b"dummy audio" in response.data
