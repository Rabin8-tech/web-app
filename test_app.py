import pytest
from app import app, users_db

@pytest.fixture
def client():
    """Provide a test client for the Flask app."""
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test that the home page (/) renders the login page."""
    response = client.get('/')
    assert response.status_code == 200
    # Check that the login form is rendered (by looking for "Login")
    assert b"Login" in response.data

def test_login_get(client):
    """Test that a GET request to /login renders the login form with Email and Password fields."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Email" in response.data
    assert b"Password" in response.data

def test_login_post_redirect(client):
    """Test that a valid login POST request logs in the user and redirects to /dashboard."""
    # Create a test user in the in-memory users_db
    test_email = "test@example.com"
    test_password = "testpass"
    users_db[test_email] = {"name": "Test User", "password": test_password}
    
    response = client.post(
        '/login',
        data={'email': test_email, 'password': test_password},
        follow_redirects=True
    )
    assert response.status_code == 200
    # The dashboard page should be rendered; check for dashboard content
    assert b"Dashboard" in response.data or b"Welcome" in response.data
    # Check that the user's name or email appears on the dashboard
    assert b"Test User" in response.data or b"test@example.com" in response.data

def test_dashboard_without_login(client):
    """Test that accessing /dashboard without being logged in redirects to the login page."""
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    # Since no user is logged in, the login page should be rendered.
    assert b"Login" in response.data
    # (Flash messages may not be rendered in the template, so we do not assert for them.)
