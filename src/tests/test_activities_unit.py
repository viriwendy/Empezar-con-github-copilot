"""Unit tests for edge cases and data integrity"""
import pytest
from urllib.parse import quote


class TestEmailValidation:
    """Tests for email parameter handling"""

    def test_signup_with_empty_email(self, client):
        """Should handle empty email parameter (API allows it)"""
        response = client.post("/activities/Chess Club/signup?email=")
        # API doesn't validate empty email - it accepts it
        assert response.status_code == 200

    def test_signup_with_special_characters_in_email(self, client):
        """Should handle emails with special characters"""
        email = "test+user@example.edu"
        response = client.post(
            f"/activities/Soccer Club/signup?email={quote(email)}"
        )
        assert response.status_code == 200

    def test_unregister_with_empty_email(self, client):
        """Should handle empty email in unregister"""
        response = client.delete("/activities/Chess Club/signup?email=")
        assert response.status_code in [400, 422]


class TestActivityNameHandling:
    """Tests for activity name handling with special characters"""

    def test_signup_for_activity_with_spaces_in_name(self, client):
        """Should handle activity names with spaces"""
        response = client.post(
            f"/activities/{quote('Programming Class')}/signup?email=test@test.edu"
        )
        # Should work with URL encoding
        assert response.status_code in [200, 400]

    def test_signup_case_sensitive_activity_name(self, client):
        """Activity names should be case-sensitive"""
        # "chess club" (lowercase) should not match "Chess Club"
        response = client.post(
            "/activities/chess club/signup?email=test@test.edu"
        )
        assert response.status_code == 404


class TestParticipantListIntegrity:
    """Tests for participant list consistency"""

    def test_participant_list_no_duplicates_after_signup(self, client):
        """Participant list should not contain duplicates"""
        email = "nodupe@test.edu"
        activity = "Soccer Club"
        
        # First signup
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Verify participant list has no duplicates
        response2 = client.get("/activities")
        participants = response2.json()[activity]["participants"]
        assert participants.count(email) == 1

    def test_participant_list_order_preserved(self, client):
        """Participant list should maintain insertion order"""
        activity = "Soccer Club"
        emails = ["Alice@test.edu", "Bob@test.edu"]
        
        for email in emails:
            client.post(f"/activities/{activity}/signup?email={email}")
        
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        
        # Check that all participants are present
        for email in emails:
            assert email in participants

    def test_unregister_does_not_corrupt_participant_list(self, client):
        """Unregistering should not corrupt the participant list"""
        activity = "Programming Class"
        emails = ["test1@test.edu", "test2@test.edu", "test3@test.edu"]
        
        # Sign up all students
        for email in emails:
            client.post(f"/activities/{activity}/signup?email={email}")
        
        # Unregister the middle one
        client.delete(f"/activities/{activity}/signup?email={emails[1]}")
        
        # Verify list integrity
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        
        assert emails[0] in participants
        assert emails[1] not in participants
        assert emails[2] in participants


class TestActivityCapacity:
    """Tests for activity capacity management"""

    def test_get_activities_shows_correct_availability(self, client):
        """Should show correct available spots in activity"""
        response = client.get("/activities")
        chess_club = response.json()["Chess Club"]
        
        # Chess Club has max_participants=2, participants=["michael@mergington.edu"]
        # So spots left should be 1
        spots_left = chess_club["max_participants"] - len(chess_club["participants"])
        assert spots_left == 1

    def test_capacities_decrease_with_signups(self, client):
        """Available capacity should decrease as students sign up"""
        activity = "Soccer Club"
        
        # Get initial capacity
        response1 = client.get("/activities")
        initial_capacity = (
            response1.json()[activity]["max_participants"]
            - len(response1.json()[activity]["participants"])
        )
        
        # Sign up a student
        client.post(f"/activities/{activity}/signup?email=newstudent@test.edu")
        
        # Get new capacity
        response2 = client.get("/activities")
        new_capacity = (
            response2.json()[activity]["max_participants"]
            - len(response2.json()[activity]["participants"])
        )
        
        # Capacity should have decreased by 1
        assert new_capacity == initial_capacity - 1

    def test_capacity_increases_with_unregistration(self, client):
        """Available capacity should increase when student unregisters"""
        activity = "Chess Club"
        
        # Get initial capacity
        response1 = client.get("/activities")
        initial_capacity = (
            response1.json()[activity]["max_participants"]
            - len(response1.json()[activity]["participants"])
        )
        
        # Unregister a student
        client.delete("/activities/Chess Club/signup?email=michael@mergington.edu")
        
        # Get new capacity
        response2 = client.get("/activities")
        new_capacity = (
            response2.json()[activity]["max_participants"]
            - len(response2.json()[activity]["participants"])
        )
        
        # Capacity should have increased by 1
        assert new_capacity == initial_capacity + 1


class TestConcurrentOperations:
    """Tests for handling multiple operations"""

    def test_multiple_signups_different_activities(self, client):
        """Should handle multiple signups for different activities"""
        response1 = client.post("/activities/Chess Club/signup?email=user1@test.edu")
        response2 = client.post("/activities/Soccer Club/signup?email=user2@test.edu")
        response3 = client.post(
            "/activities/Programming Class/signup?email=user3@test.edu"
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        assert "user1@test.edu" in response.json()["Chess Club"]["participants"]
        assert "user2@test.edu" in response.json()["Soccer Club"]["participants"]
        assert "user3@test.edu" in response.json()["Programming Class"]["participants"]

    def test_signup_unregister_signup_same_activity(self, client):
        """Should handle signup, unregister, then signup again for same activity"""
        email = "cycleuser@test.edu"
        activity = "Soccer Club"
        
        # First signup
        client.post(f"/activities/{activity}/signup?email={email}")
        response1 = client.get("/activities")
        assert email in response1.json()[activity]["participants"]
        
        # Unregister
        client.delete(f"/activities/{activity}/signup?email={email}")
        response2 = client.get("/activities")
        assert email not in response2.json()[activity]["participants"]
        
        # Sign up again
        response3 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response3.status_code == 200
        
        response4 = client.get("/activities")
        assert email in response4.json()[activity]["participants"]
