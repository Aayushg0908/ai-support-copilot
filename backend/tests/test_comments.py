"""
Tests for comment endpoints.

Covers:
- Create comment on ticket
- Create reply to comment (threaded)
- List comments (flat and threaded)
- Update comment
- Delete comment
- Authorization (only author can edit/delete)
"""

from fastapi.testclient import TestClient


class TestCreateComment:
    """Tests for POST /api/v1/tickets/{id}/comments"""
    
    def test_create_comment_success(self, client: TestClient, test_ticket):
        """Should add a comment to a ticket."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={
                "body": "This is a test comment",
                "is_internal": False,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["body"] == "This is a test comment"
        assert data["ticket_id"] == ticket_id
        assert data["is_internal"] == False
        assert data["parent_id"] is None  # Top-level comment
        assert data["user_name"] == "Test User"
    
    def test_create_reply_to_comment(self, client: TestClient, test_ticket):
        """Should create a reply to an existing comment."""
        ticket_id = str(test_ticket["ticket"].id)
        
        # First, create a parent comment
        parent_response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "Parent comment"},
        )
        parent_id = parent_response.json()["id"]
        
        # Now reply to it
        response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={
                "body": "This is a reply",
                "parent_id": parent_id,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["parent_id"] == parent_id
        assert data["body"] == "This is a reply"
    
    def test_create_internal_note(self, client: TestClient, test_ticket):
        """Should create an internal note."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={
                "body": "Internal agent note",
                "is_internal": True,
            },
        )
        
        assert response.status_code == 201
        assert response.json()["is_internal"] == True
    
    def test_create_comment_without_auth(self, client: TestClient, test_ticket):
        """Should reject without token."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            json={"body": "Unauthorized comment"},
        )
        
        assert response.status_code == 401


class TestListComments:
    """Tests for GET /api/v1/tickets/{id}/comments"""
    
    def test_list_comments_flat(self, client: TestClient, test_ticket):
        """Should list comments in flat mode."""
        ticket_id = str(test_ticket["ticket"].id)
        
        # Create a couple of comments
        client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "Comment 1"},
        )
        client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "Comment 2"},
        )
        
        # List comments
        response = client.get(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "comments" in data
        assert data["total"] >= 2
    
    def test_list_comments_threaded(self, client: TestClient, test_ticket):
        """Should list comments in threaded mode."""
        ticket_id = str(test_ticket["ticket"].id)
        
        # Create parent + reply
        parent_response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "Parent"},
        )
        parent_id = parent_response.json()["id"]
        
        client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "Reply", "parent_id": parent_id},
        )
        
        # Get threaded view
        response = client.get(
            f"/api/v1/tickets/{ticket_id}/comments?threaded=true",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # First comment should have replies
        top_comment = data["comments"][0]
        assert len(top_comment["replies"]) >= 1
        assert top_comment["replies"][0]["body"] == "Reply"


class TestUpdateComment:
    """Tests for PUT /api/v1/comments/{id}"""
    
    def test_update_own_comment(self, client: TestClient, test_ticket):
        """Should update own comment."""
        ticket_id = str(test_ticket["ticket"].id)
        
        # Create a comment
        create_response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "Original body"},
        )
        comment_id = create_response.json()["id"]
        
        # Update it
        response = client.put(
            f"/api/v1/comments/{comment_id}",
            headers=test_ticket["headers"],
            json={"body": "Updated body"},
        )
        
        assert response.status_code == 200
        assert response.json()["body"] == "Updated body"
    
    def test_cannot_update_others_comment(self, client: TestClient, db, test_ticket):
        """Should prevent editing someone else's comment."""
        from app.models.user import User, UserRole
        from app.models.organization import Organization
        from app.core.security import hash_password, create_access_token
        
        ticket_id = str(test_ticket["ticket"].id)
        
        # Create comment as test user
        create_response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "My comment"},
        )
        comment_id = create_response.json()["id"]
        
        # Create another user in the same org
        other_org = db.query(Organization).first()
        other_user = User(
            org_id=other_org.id,
            email="other@test.com",
            password_hash=hash_password("TestPass1"),
            full_name="Other User",
            role=UserRole.AGENT,
        )
        db.add(other_user)
        db.commit()
        
        other_token = create_access_token(
            data={"sub": str(other_user.id), "org_id": str(other_org.id)}
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Try to edit as other user
        response = client.put(
            f"/api/v1/comments/{comment_id}",
            headers=other_headers,
            json={"body": "Hacked comment"},
        )
        
        assert response.status_code == 403


class TestDeleteComment:
    """Tests for DELETE /api/v1/comments/{id}"""
    
    def test_delete_own_comment(self, client: TestClient, test_ticket):
        """Should delete own comment."""
        ticket_id = str(test_ticket["ticket"].id)
        
        # Create a comment
        create_response = client.post(
            f"/api/v1/tickets/{ticket_id}/comments",
            headers=test_ticket["headers"],
            json={"body": "To be deleted"},
        )
        comment_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/api/v1/comments/{comment_id}",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True