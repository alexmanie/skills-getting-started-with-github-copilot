"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
    })
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_success(self, client):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert data["Chess Club"]["max_participants"] == 12
        assert len(data["Chess Club"]["participants"]) == 2

    def test_activities_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify student was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_student(self, client):
        """Test that signing up twice fails"""
        email = "michael@mergington.edu"
        
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_multiple_students(self, client):
        """Test multiple students can sign up for the same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/Chess%20Club/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        participants = activities_data["Chess Club"]["participants"]
        
        for email in emails:
            assert email in participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"
        
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
        
        # Verify student was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]

    def test_unregister_nonexistent_student(self, client):
        """Test unregistering a student not in the activity fails"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity fails"""
        response = client.delete(
            "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_and_resignup(self, client):
        """Test that a student can unregister and sign up again"""
        email = "michael@mergington.edu"
        
        # Unregister
        response = client.delete(
            f"/activities/Chess%20Club/unregister?email={email}"
        )
        assert response.status_code == 200
        
        # Sign up again
        response = client.post(
            f"/activities/Chess%20Club/signup?email={email}"
        )
        assert response.status_code == 200
        
        # Verify student is registered
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]


class TestCompleteWorkflow:
    """Integration tests for complete workflows"""

    def test_full_student_lifecycle(self, client):
        """Test complete student registration lifecycle"""
        email = "lifecycle@mergington.edu"
        activity = "Programming Class"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_participants = initial_response.json()[activity]["participants"]
        assert email not in initial_participants
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        after_signup_participants = after_signup.json()[activity]["participants"]
        assert email in after_signup_participants
        assert len(after_signup_participants) == len(initial_participants) + 1
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        after_unregister = client.get("/activities")
        after_unregister_participants = after_unregister.json()[activity]["participants"]
        assert email not in after_unregister_participants
        assert len(after_unregister_participants) == len(initial_participants)

    def test_participant_count_tracking(self, client):
        """Test that participant counts are accurately tracked"""
        activity = "Chess Club"
        
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        # Add 3 students
        for i in range(3):
            client.post(
                f"/activities/Chess%20Club/signup?email=student{i}@mergington.edu"
            )
        
        # Verify count increased
        after_signup = client.get("/activities")
        after_count = len(after_signup.json()[activity]["participants"])
        assert after_count == initial_count + 3
        
        # Remove 2 students
        client.delete("/activities/Chess%20Club/unregister?email=student0@mergington.edu")
        client.delete("/activities/Chess%20Club/unregister?email=student1@mergington.edu")
        
        # Verify count decreased
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity]["participants"])
        assert final_count == initial_count + 1
