import os
os.environ['MYSQL_HOST'] = '127.0.0.1'
os.environ['MYSQL_USER'] = 'root'
os.environ['MYSQL_PASSWORD'] = 'rabin8866'
os.environ['MYSQL_DB'] = 'test_mydatabase'
os.environ['MYSQL_PORT'] = '3306'


import pytest
import re
import requests
from flask import session
from app import app, mysql  # Import your Flask app

@pytest.fixture
def client():
    """Configures a test client and prepares the database."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    app.config['MYSQL_DB'] = 'test_mydatabase'  # Ensure test database exists

    with app.app_context():
        mysql.connection.ping()
        cursor = mysql.connection.cursor()
        cursor.execute("DROP TABLE IF EXISTS users;")
        cursor.execute("""
            CREATE TABLE users (
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                email VARCHAR(255) NOT NULL PRIMARY KEY,
                password VARCHAR(255) NOT NULL
            );
        """)
        mysql.connection.commit()

        with app.test_client() as client:
            yield client

        cursor.execute("DROP TABLE IF EXISTS users;")
        mysql.connection.commit()

def test_register(client):
    """Tests user registration."""
    response = client.post("/register", data={
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    assert b"Registration successful" in response.data

    # Verify password is hashed
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT password FROM users WHERE email = %s", ("test@example.com",))
    stored_password = cursor.fetchone()["password"]
    assert not stored_password == "Password123!"
    assert re.match(r"^\$2[abxy]\$", stored_password)

def test_login(client):
    """Tests login functionality."""
    client.post("/register", data={
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    response = client.post("/login", data={
        "email": "test@example.com",
        "password": "Password123!"
    }, follow_redirects=True)

    assert b"Login successful" in response.data
    with client.session_transaction() as sess:
        assert sess["user_id"] == "test@example.com"

def test_sql_injection_prevention(client):
    """Tests SQL injection prevention."""
    malicious_email = "malicious@example.com' --"
    response = client.post("/register", data={
        "first_name": "Malicious",
        "last_name": "User",
        "email": malicious_email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT email FROM users WHERE email = %s", (malicious_email,))
    result = cursor.fetchone()

    assert result is None, "SQL injection should have been prevented!"

def test_dashboard_access(client):
    """Tests dashboard access."""
    client.post("/register", data={
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    client.post("/login", data={
        "email": "test@example.com",
        "password": "Password123!"
    }, follow_redirects=True)

    response = client.get("/dashboard", follow_redirects=True)
    assert b"Search" in response.data

def test_dashboard_openverse_search(client, monkeypatch):
    """Tests Openverse search functionality."""
    class DummyResponse:
        def __init__(self, results, status_code=200):
            self._results = results
            self.status_code = status_code

        def json(self):
            return {"results": self._results}

    def dummy_get(url, headers):
        if "/images/" in url:
            return DummyResponse([{"title": "dummy image"}])
        elif "/audio/" in url:
            return DummyResponse([{"title": "dummy audio"}])
        return DummyResponse([], status_code=404)

    monkeypatch.setattr("requests.get", dummy_get)

    client.post("/register", data={
        "first_name": "Search",
        "last_name": "Tester",
        "email": "search@test.com",
        "password": "Password123!",
        "confirm_password": "Password123!"
    }, follow_redirects=True)

    client.post("/login", data={
        "email": "search@test.com",
        "password": "Password123!"
    }, follow_redirects=True)

    response = client.post("/dashboard", data={"query": "nature"}, follow_redirects=True)
    assert b"dummy image" in response.data
    assert b"dummy audio" in response.data