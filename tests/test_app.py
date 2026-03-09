import pytest
import time
from fastapi.testclient import TestClient
from src.app import app

# Test client fixture is in conftest.py

@pytest.mark.parametrize("activity_name", [
    "Chess Club", "Programming Class", "Gym Class", "Basketball Team",
    "Tennis Club", "Art Studio", "Music Band", "Science Club", "Debate Team"
])
def test_get_activities_contains_expected_activities(client, activity_name):
    """Test that GET /activities returns expected activities"""
    # Arrange: No special setup needed
    
    # Act: Make request to get activities
    response = client.get("/activities")
    
    # Assert: Check response and content
    assert response.status_code == 200
    assert activity_name in response.json()

def test_get_activities_structure(client):
    """Test that activities have expected schema with all required fields"""
    # Arrange: No special setup needed
    
    # Act: Make request to get activities
    response = client.get("/activities")
    
    # Assert: Check response structure
    assert response.status_code == 200
    
    activities = response.json()
    for activity_name, activity in activities.items():
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

# Signup tests
def test_signup_new_student_success(client, reset_activities):
    """Test successful signup of a new student to an activity"""
    # Arrange: Choose an activity and new student email
    activity_name = "Art Studio"
    new_email = "new_artist@mergington.edu"
    
    # Act: Attempt to sign up
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": new_email}
    )
    
    # Assert: Check success response and state change
    assert response.status_code == 200
    assert "Signed up" in response.json()["message"]
    
    # Verify participant was added
    activities_response = client.get("/activities")
    activities = activities_response.json()
    assert new_email in activities[activity_name]["participants"]

def test_signup_duplicate_student_fails(client, reset_activities):
    """Test that signing up a student twice for the same activity fails"""
    # Arrange: Use an email already signed up
    activity_name = "Chess Club"
    existing_email = "michael@mergington.edu"  # Already in participants
    
    # Act: Attempt duplicate signup
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": existing_email}
    )
    
    # Assert: Check failure response
    assert response.status_code == 400
    assert "already signed up" in response.json()["detail"]

def test_signup_nonexistent_activity_fails(client, reset_activities):
    """Test that signing up for a non-existent activity fails"""
    # Arrange: Use invalid activity name
    invalid_activity = "Nonexistent Activity"
    email = "student@mergington.edu"
    
    # Act: Attempt signup
    response = client.post(
        f"/activities/{invalid_activity}/signup",
        params={"email": email}
    )
    
    # Assert: Check failure response
    assert response.status_code == 404
    assert "Activity not found" in response.json()["detail"]

def test_signup_activity_full_fails(client, reset_activities):
    """Test that signing up when activity is at max capacity fails"""
    # Arrange: Fill up an activity to max capacity
    activity_name = "Basketball Team"  # max_participants: 15, currently 1 participant
    base_participants = 1  # alex@mergington.edu
    
    # Fill to max
    for i in range(14):  # 15 - 1 = 14 more needed to reach max
        email = f"player{i}@mergington.edu"
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
    
    # Act: Try to add one more (should fail)
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "extra_player@mergington.edu"}
    )
    
    # Assert: Check failure response
    assert response.status_code == 400
    assert "Activity is full" in response.json()["detail"]

def test_signup_activity_at_max_minus_one_succeeds(client, reset_activities):
    """Test that signing up when activity has space available succeeds"""
    # Arrange: Fill to max-1
    activity_name = "Debate Team"  # max_participants: 12, currently 2 participants
    base_participants = 2
    
    # Fill to max-1 (12 - 2 - 1 = 9 more to reach 11)
    for i in range(9):
        email = f"debater{i}@mergington.edu"
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )
        assert response.status_code == 200
    
    # Act: Add the last spot (should succeed, reaching exactly max)
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "last_debater@mergington.edu"}
    )
    
    # Assert: Check success
    assert response.status_code == 200
    assert "Signed up" in response.json()["message"]

# Delete tests
def test_remove_signup_success(client, reset_activities):
    """Test successful removal of a student from an activity"""
    # Arrange: Sign up a student first
    activity_name = "Tennis Club"
    email = "new_player@mergington.edu"
    client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    
    # Act: Remove the student
    response = client.delete(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    
    # Assert: Check success and state change
    assert response.status_code == 200
    assert "Removed" in response.json()["message"]
    
    # Verify participant was removed
    activities_response = client.get("/activities")
    activities = activities_response.json()
    assert email not in activities[activity_name]["participants"]

def test_remove_signup_not_signed_up_fails(client, reset_activities):
    """Test that removing a student not signed up fails"""
    # Arrange: Use email not in activity
    activity_name = "Chess Club"
    not_signed_up_email = "not_here@mergington.edu"
    
    # Act: Attempt removal
    response = client.delete(
        f"/activities/{activity_name}/signup",
        params={"email": not_signed_up_email}
    )
    
    # Assert: Check failure
    assert response.status_code == 400
    assert "not signed up" in response.json()["detail"]

def test_remove_signup_nonexistent_activity_fails(client, reset_activities):
    """Test that removing from non-existent activity fails"""
    # Arrange: Invalid activity
    invalid_activity = "Fake Activity"
    email = "student@mergington.edu"
    
    # Act: Attempt removal
    response = client.delete(
        f"/activities/{invalid_activity}/signup",
        params={"email": email}
    )
    
    # Assert: Check failure
    assert response.status_code == 404
    assert "Activity not found" in response.json()["detail"]

# Integration test
def test_full_signup_view_delete_workflow(client, reset_activities):
    """Test complete workflow: signup -> view updated list -> delete -> view updated list"""
    # Arrange: Choose activity and student
    activity_name = "Science Club"
    email = "new_scientist@mergington.edu"
    
    # Act & Assert: Initial state - email not in participants
    response = client.get("/activities")
    activities = response.json()
    assert email not in activities[activity_name]["participants"]
    initial_count = len(activities[activity_name]["participants"])
    
    # Act: Sign up student
    signup_response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    
    # Assert: Signup successful
    assert signup_response.status_code == 200
    
    # Act & Assert: View updated list - email now in participants
    response = client.get("/activities")
    activities = response.json()
    assert email in activities[activity_name]["participants"]
    assert len(activities[activity_name]["participants"]) == initial_count + 1
    
    # Act: Delete student
    delete_response = client.delete(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    
    # Assert: Delete successful
    assert delete_response.status_code == 200
    
    # Act & Assert: View final list - email removed, back to original count
    response = client.get("/activities")
    activities = response.json()
    assert email not in activities[activity_name]["participants"]
    assert len(activities[activity_name]["participants"]) == initial_count

# Performance tests
def test_get_activities_performance(client, reset_activities):
    """Test that GET /activities responds quickly (< 100ms)"""
    # Arrange: No special setup
    
    # Act: Time the request
    start_time = time.time()
    response = client.get("/activities")
    end_time = time.time()
    
    # Assert: Check response and performance
    assert response.status_code == 200
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
    assert response_time < 100, f"Response took {response_time:.2f}ms, expected < 100ms"

def test_signup_performance(client, reset_activities):
    """Test that POST signup responds quickly (< 100ms)"""
    # Arrange: Valid signup data
    activity_name = "Art Studio"
    email = "perf_test@mergington.edu"
    
    # Act: Time the request
    start_time = time.time()
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    end_time = time.time()
    
    # Assert: Check response and performance
    assert response.status_code == 200
    response_time = (end_time - start_time) * 1000
    assert response_time < 100, f"Response took {response_time:.2f}ms, expected < 100ms"

def test_delete_performance(client, reset_activities):
    """Test that DELETE signup responds quickly (< 100ms)"""
    # Arrange: Sign up first, then time delete
    activity_name = "Music Band"
    email = "perf_delete@mergington.edu"
    client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    
    # Act: Time the delete request
    start_time = time.time()
    response = client.delete(
        f"/activities/{activity_name}/signup",
        params={"email": email}
    )
    end_time = time.time()
    
    # Assert: Check response and performance
    assert response.status_code == 200
    response_time = (end_time - start_time) * 1000
    assert response_time < 100, f"Response took {response_time:.2f}ms, expected < 100ms"