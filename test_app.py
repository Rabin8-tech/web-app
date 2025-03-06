import pytest
from app import app

@pytest.fixture
def client():
    """Fixture to provide a test client for Flask."""
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test the home page (/) route which renders the login page."""
    response = client.get('/')
    assert response.status_code == 200
    # Check for expected content in the login page
    assert b"Login" in response.data

def test_login_get(client):
    """Test GET request to the /login route."""
    response = client.get('/login')
    assert response.status_code == 200
    # Check that the login form fields are present
    assert b"Email" in response.data
    assert b"Password" in response.data

def test_login_post_redirect(client):
    """Test POST request to /login with valid credentials redirects to /dashboard."""
    # Simulate a POST request with sample credentials
    response = client.post(
        '/login',
        data={'email': 'test@example.com', 'password': 'testpass'},
        follow_redirects=True
    )
    # The response should be the dashboard page
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    # Check if the user's email is displayed on the dashboard
    assert b"test@example.com" in response.data

def test_dashboard_without_login(client):
    """Test that accessing the dashboard without login redirects to the login page."""
    response = client.get('/dashboard', follow_redirects=True)
    # Since no user is logged in, it should redirect to the login page
    assert response.status_code == 200
    assert b"Login" in response.data
    # Optionally, check for the flash message if it's rendered on the page
    assert b"Please log in first" in response.data
