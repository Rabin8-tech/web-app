import pytest
from flask import session
from app import app, mysql


@pytest.fixture
def client():
    """Fixture to create a test client."""
    app.config['TESTING'] = True
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = '8966'  # Update with your MySQL password
    app.config['MYSQL_DB'] = 'mydatabase'  # Use a test database
    mysql.init_app(app)

    with app.test_client() as client:
        with app.app_context():
            # Set up the test database, creating a 'users' table
            cursor = mysql.connection.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, email VARCHAR(255), password VARCHAR(255))")
            mysql.connection.commit()
        yield client

        with app.app_context():
            # Clean up after the test
            cursor.execute("DROP TABLE IF EXISTS users")
            mysql.connection.commit()


def test_register(client):
    """Test user registration."""
    response = client.post('/register', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)
    assert b'Registration successful' in response.data

    # Ensure the user is in the database
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", ('test@example.com',))
    user = cursor.fetchone()
    assert user is not None


def test_register_existing_user(client):
    """Test registering an already registered user."""
    client.post('/register', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)
    response = client.post('/register', data={'email': 'test@example.com', 'password': 'newpassword'}, follow_redirects=True)
    assert b'Email already registered' in response.data


def test_login(client):
    """Test user login with correct credentials."""
    # Register the user first
    client.post('/register', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)

    # Login with correct credentials
    response = client.post('/login', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)
    assert b'Login successful' in response.data


def test_login_unregistered_user(client):
    """Test login for unregistered users."""
    response = client.post('/login', data={'email': 'unregistered@example.com', 'password': 'password'}, follow_redirects=True)
    assert b'User not registered' in response.data


def test_login_incorrect_password(client):
    """Test login with an incorrect password."""
    # Register the user first
    client.post('/register', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)

    # Attempt login with incorrect password
    response = client.post('/login', data={'email': 'test@example.com', 'password': 'wrongpassword'}, follow_redirects=True)
    assert b'Incorrect password' in response.data


def test_dashboard_access(client):
    """Test accessing the dashboard."""
    # Register and login the user first
    client.post('/register', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)
    client.post('/login', data={'email': 'test@example.com', 'password': 'password'}, follow_redirects=True)

    # Access the dashboard
    response = client.get('/dashboard', follow_redirects=True)
    assert b'Dashboard' in response.data


def test_dashboard_access_without_login(client):
    """Test accessing the dashboard without logging in."""
    response = client.get('/dashboard', follow_redirects=True)
    assert b'Please log in first' in response.data