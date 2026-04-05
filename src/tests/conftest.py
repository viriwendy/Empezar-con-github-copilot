"""Shared test fixtures and configuration for the API tests"""
import pytest
from fastapi.testclient import TestClient
from app import app, activities


@pytest.fixture
def client():
    """Provide a TestClient for API testing"""
    return TestClient(app)


@pytest.fixture
def sample_activities():
    """Provide fresh sample activities data for each test"""
    return {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 2,  # Small number for testing capacity
            "participants": ["michael@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 3,
            "participants": ["emma@mergington.edu"]
        },
        "Soccer Club": {
            "description": "Train and play soccer matches",
            "schedule": "Wednesdays and Fridays, 3:00 PM - 4:30 PM",
            "max_participants": 2,
            "participants": []
        },
    }


@pytest.fixture(autouse=True)
def reset_activities(sample_activities):
    """Reset activities data before each test to ensure isolation"""
    activities.clear()
    activities.update(sample_activities)
    yield
    activities.clear()
    activities.update(sample_activities)
