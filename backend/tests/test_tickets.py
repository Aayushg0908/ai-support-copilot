"""
Tests for ticket endpoints.

Covers:
- Create ticket
- List tickets with filters
- Get ticket details
- Update ticket
- Status changes
- Assignment
- Delete (close) ticket
- Authorization checks
"""

from fastapi.testclient import TestClient


class TestCreateTicket:
    """Tests for POST /api/v1/tickets"""
    
    def test_create_ticket_success(self, client: TestClient, test_user):
        """Should create a new ticket."""
        response = client.post(
            "/api/v1/tickets/",
            headers=test_user["headers"],
            json={
                "title": "Test support ticket",
                "description": "This is a test ticket for testing purposes",
                "priority": "high",
                "category": "support",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["title"] == "Test support ticket"
        assert data["status"] == "open"
        assert data["priority"] == "high"
        assert data["category"] == "support"
        assert data["created_by"] == str(test_user["user"].id)
    
    def test_create_ticket_minimal(self, client: TestClient, test_user):
        """Should create ticket with only required fields."""
        response = client.post(
            "/api/v1/tickets/",
            headers=test_user["headers"],
            json={
                "title": "Minimal ticket",
                "description": "Just enough description here",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "open"
        assert data["priority"] == "medium"  # Default
    
    def test_create_ticket_without_auth(self, client: TestClient):
        """Should reject without token."""
        response = client.post(
            "/api/v1/tickets/",
            json={
                "title": "Unauthorized ticket",
                "description": "Should not be created",
            },
        )
        
        assert response.status_code == 401
    
    def test_create_ticket_short_title(self, client: TestClient, test_user):
        """Should reject title shorter than 5 characters."""
        response = client.post(
            "/api/v1/tickets/",
            headers=test_user["headers"],
            json={
                "title": "Hi",  # Too short
                "description": "Valid description here",
            },
        )
        
        assert response.status_code == 422


class TestListTickets:
    """Tests for GET /api/v1/tickets"""
    
    def test_list_tickets(self, client: TestClient, test_ticket):
        """Should list tickets for the organization."""
        response = client.get(
            "/api/v1/tickets/",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "tickets" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 1
    
    def test_list_tickets_filter_by_status(self, client: TestClient, test_ticket):
        """Should filter tickets by status."""
        response = client.get(
            "/api/v1/tickets/?status=open",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket["status"] == "open"
    
    def test_list_tickets_filter_by_priority(self, client: TestClient, test_ticket):
        """Should filter tickets by priority."""
        response = client.get(
            "/api/v1/tickets/?priority=medium",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for ticket in data["tickets"]:
            assert ticket["priority"] == "medium"
    
    def test_list_tickets_search(self, client: TestClient, test_ticket):
        """Should search tickets by title."""
        response = client.get(
            "/api/v1/tickets/?search=Test Ticket",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    def test_list_tickets_pagination(self, client: TestClient, test_user):
        """Should paginate results."""
        # Create 5 tickets
        for i in range(5):
            client.post(
                "/api/v1/tickets/",
                headers=test_user["headers"],
                json={
                    "title": f"Ticket {i}",
                    "description": f"Description for ticket {i}",
                },
            )
        
        # Get page 1 with 2 per page
        response = client.get(
            "/api/v1/tickets/?page=1&per_page=2",
            headers=test_user["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["tickets"]) == 2
        assert data["per_page"] == 2
    
    def test_list_tickets_without_auth(self, client: TestClient):
        """Should reject without token."""
        response = client.get("/api/v1/tickets/")
        assert response.status_code == 401


class TestGetTicket:
    """Tests for GET /api/v1/tickets/{id}"""
    
    def test_get_ticket_success(self, client: TestClient, test_ticket):
        """Should return ticket details."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.get(
            f"/api/v1/tickets/{ticket_id}",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == ticket_id
        assert data["title"] == "Test Ticket"
        assert "creator_name" in data
        assert "comment_count" in data
    
    def test_get_ticket_not_found(self, client: TestClient, test_user):
        """Should return 404 for non-existent ticket."""
        response = client.get(
            "/api/v1/tickets/00000000-0000-0000-0000-000000000000",
            headers=test_user["headers"],
        )
        
        assert response.status_code == 404


class TestUpdateTicket:
    """Tests for PUT /api/v1/tickets/{id}"""
    
    def test_update_ticket_title(self, client: TestClient, test_ticket):
        """Should update ticket title."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.put(
            f"/api/v1/tickets/{ticket_id}",
            headers=test_ticket["headers"],
            json={"title": "Updated Title"},
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
    
    def test_update_ticket_priority(self, client: TestClient, test_ticket):
        """Should update ticket priority."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.put(
            f"/api/v1/tickets/{ticket_id}",
            headers=test_ticket["headers"],
            json={"priority": "critical"},
        )
        
        assert response.status_code == 200
        assert response.json()["priority"] == "critical"


class TestTicketStatus:
    """Tests for PATCH /api/v1/tickets/{id}/status"""
    
    def test_change_status_to_in_progress(self, client: TestClient, test_ticket):
        """Should change ticket status."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            headers=test_ticket["headers"],
            json={"status": "in_progress"},
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"
    
    def test_resolve_ticket_sets_timestamp(self, client: TestClient, test_ticket):
        """Should set resolved_at when resolving."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.patch(
            f"/api/v1/tickets/{ticket_id}/status",
            headers=test_ticket["headers"],
            json={"status": "resolved"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None


class TestDeleteTicket:
    """Tests for DELETE /api/v1/tickets/{id}"""
    
    def test_close_ticket(self, client: TestClient, test_ticket):
        """Should close ticket (soft delete)."""
        ticket_id = str(test_ticket["ticket"].id)
        response = client.delete(
            f"/api/v1/tickets/{ticket_id}",
            headers=test_ticket["headers"],
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify ticket is now closed
        get_response = client.get(
            f"/api/v1/tickets/{ticket_id}",
            headers=test_ticket["headers"],
        )
        assert get_response.json()["status"] == "closed"