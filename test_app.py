import pytest
from app import app

@pytest.fixture
def client():
    """Fixture to provide a test client for Flask."""
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test the home page (/) route which renders the index.html template."""
    
    # Send a GET request to the home page route
    response = client.get('/')
    
    # Check if the status code is 200 (OK)
    assert response.status_code == 200
    
    # Check if the rendered content contains specific text from index.html
    assert b"Welcome to Web App!" in response.data  # Check for the <h1> text
    assert b"This is the initial Flask setup." in response.data  # Check for the <p> text
