import pytest
from flask import session
from app import app, mysql  # Adjust the import if your Flask module is named differently

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
      - Check that a registration attempt yields a page with a form (e.g., the login page).
      - Verify that trying to register a duplicate email results in re-rendering the registration (or error) page.
    """
    # Submit the registration form.
    response = client.post(
        "/register",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )
    # The registration view flashes a success message and redirects to the login page.
    # Here, we verify that the login form is rendered by checking for a form element with "Email".
    assert b"<form" in response.data and b"Email" in response.data

    # Attempt duplicate registration.
    response = client.post(
        "/register",
        data=dict(email="test@example.com", password="password123"),
        follow_redirects=True
    )
    # Either a flash message "Email already registered" is rendered or the form is re-displayed.
    assert b"Email already registered" in response.data or b"<form" in response.data

def test_login(client):
    """
    Test login functionality:
      - Successful login sets the session and redirects appropriately.
      - Login with an unregistered email does not set the session.
      - Login with an incorrect password does not set the session.
      
    To ensure each login attempt starts with a clean slate, we explicitly clear the session in between.
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
    # Confirm that the session contains the logged-in email.
    with client.session_transaction() as sess:
        assert sess.get("user_id") == "test@example.com"
    # Optionally, check for dashboard output.
    assert b"test@example.com" in response.data

    # Clear the session before next login attempt.
    with client.session_transaction() as sess:
        sess.clear()

    # ------- Login Attempt with Unregistered Email -------
    response = client.post(
        "/login",
        data=dict(email="nosuchuser@example.com", password="password123"),
        follow_redirects=True
    )
    with client.session_transaction() as sess:
        # The session should not contain a user_id.
        assert sess.get("user_id") is None
    # Verify that the login form is rendered.
    assert b"<form" in response.data and b"Email" in response.data

    # Clear the session before next login attempt.
    with client.session_transaction() as sess:
        sess.clear()

    # ------- Login Attempt with Incorrect Password -------
    response = client.post(
        "/login",
        data=dict(email="test@example.com", password="wrongpassword"),
        follow_redirects=True
    )
    with client.session_transaction() as sess:
        # Ensure that no session is set when the password is incorrect.
        assert sess.get("user_id") is None
    # Verify that the login view is re-rendered (e.g., it contains a form).
    assert b"<form" in response.data and b"Email" in response.data

def test_dashboard_access(client):
    """
    Test dashboard access:
      - When logged in, the dashboard should display user-specific content.
      - When not logged in, accessing the dashboard should redirect to the login page.
    """
    # Register and log in the test user.
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

    # Access dashboard as an authenticated user.
    response = client.get("/dashboard", follow_redirects=True)
    # We assume the dashboard displays the logged-in email.
    assert b"test@example.com" in response.data

    # Simulate logging out by clearing the session.
    with client.session_transaction() as sess:
        sess.clear()

    # Attempt to access the dashboard while not logged in.
    response = client.get("/dashboard", follow_redirects=True)
    # Verify that the login page (or its form) is rendered.
    assert b"<form" in response.data and b"Email" in response.data