"""Integration tests for all API endpoints"""
import pytest
from fastapi.testclient import TestClient


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Should return all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Soccer Club" in data

    def test_get_activities_returns_correct_structure(self, client):
        """Should return activities with correct schema"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)

    def test_get_activities_includes_existing_participants(self, client):
        """Should include current participants in response"""
        response = client.get("/activities")
        data = response.json()
        
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "emma@mergington.edu" in data["Programming Class"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_for_activity_success(self, client):
        """Should successfully sign up a new student"""
        response = client.post(
            "/activities/Soccer Club/signup?email=john@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "john@mergington.edu" in data["message"]
        assert "Soccer Club" in data["message"]

    def test_signup_student_is_added_to_participants(self, client):
        """Should add student to activities participants list"""
        client.post("/activities/Soccer Club/signup?email=alice@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert "alice@mergington.edu" in activities["Soccer Club"]["participants"]

    def test_signup_for_nonexistent_activity_returns_404(self, client):
        """Should return 404 for activity that does not exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_student_returns_400(self, client):
        """Should return 400 when student is already signed up"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_activity_at_full_capacity(self, client):
        """Should allow signup even when activity appears full (API doesn't validate capacity)"""
        # Chess Club has max_participants=2 and michael@mergington.edu is already signed up
        # Sign up one more student to reach capacity
        response1 = client.post("/activities/Chess Club/signup?email=david@mergington.edu")
        assert response1.status_code == 200
        
        # Try to sign up another student - API allows it (doesn't validate capacity)
        response2 = client.post(
            "/activities/Chess Club/signup?email=sarah@mergington.edu"
        )
        assert response2.status_code == 200

    def test_signup_with_special_characters_in_email(self, client):
        """Should handle emails with special characters (URL encoded)"""
        response = client.post(
            "/activities/Soccer Club/signup?email=test%2Buser@mergington.edu"
        )
        assert response.status_code == 200

    def test_signup_response_structure(self, client):
        """Should return structured response with message"""
        response = client.post(
            "/activities/Soccer Club/signup?email=test@mergington.edu"
        )
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""

    def test_unregister_success(self, client):
        """Should successfully unregister a student"""
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Should remove student from participants list after unregister"""
        client.delete("/activities/Chess Club/signup?email=michael@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity_returns_404(self, client):
        """Should return 404 for activity that does not exist"""
        response = client.delete(
            "/activities/Fake Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_not_signed_up_student_returns_400(self, client):
        """Should return 400 when student is not registered"""
        response = client.delete(
            "/activities/Soccer Club/signup?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]

    def test_unregister_response_structure(self, client):
        """Should return structured response with message"""
        response = client.delete(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data


class TestActivityStateManagement:
    """Tests for activity state transitions and consistency"""

    def test_signup_then_unregister_cycle(self, client):
        """Should handle signup followed by unregister correctly"""
        email = "cycle@mergington.edu"
        activity = "Soccer Club"
        
        # Sign up
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Verify signup
        response2 = client.get("/activities")
        assert email in response2.json()[activity]["participants"]
        
        # Unregister
        response3 = client.delete(f"/activities/{activity}/signup?email={email}")
        assert response3.status_code == 200
        
        # Verify unregister
        response4 = client.get("/activities")
        assert email not in response4.json()[activity]["participants"]

    def test_multiple_student_signups(self, client):
        """Should handle multiple students signing up for same activity"""
        activity = "Soccer Club"
        students = ["alice@test.edu", "bob@test.edu", "charlie@test.edu"]
        
        for student in students:
            response = client.post(f"/activities/{activity}/signup?email={student}")
            assert response.status_code in [200, 400]  # 400 if capacity full
        
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        
        # At least one student should be registered
        assert len(participants) > 0
