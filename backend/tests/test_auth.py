"""
Tests for authentication endpoints.

Covers:
- User registration
- User login
- Token refresh
- Get current user
- Invalid credentials
- Duplicate email
"""

from fastapi.testclient import TestClient


class TestAuthRegistration:
    """Tests for POST /api/v1/auth/register"""
    
    def test_register_success(self, client: TestClient):
        """Should create a new user and return tokens."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "StrongPass1",
                "full_name": "New User",
                "organization_name": "New Corp",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Should have both tokens
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Should have user data
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["full_name"] == "New User"
        assert data["user"]["role"] == "admin"
        # Password should NOT be in response
        assert "password_hash" not in data["user"]
    
    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Should reject duplicate email with 409."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Already exists from fixture
                "password": "StrongPass1",
                "full_name": "Another User",
                "organization_name": "Another Corp",
            },
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["error"]["message"]
    
    def test_register_weak_password(self, client: TestClient):
        """Should reject weak passwords with 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "password": "weak",  # No uppercase, no digit
                "full_name": "Weak User",
                "organization_name": "Weak Corp",
            },
        )
        
        assert response.status_code == 422
    
    def test_register_invalid_email(self, client: TestClient):
        """Should reject invalid email format with 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "StrongPass1",
                "full_name": "Bad Email",
                "organization_name": "Bad Corp",
            },
        )
        
        assert response.status_code == 422


class TestAuthLogin:
    """Tests for POST /api/v1/auth/login"""
    
    def test_login_success(self, client: TestClient, test_user):
        """Should login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass1",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@example.com"
    
    def test_login_wrong_password(self, client: TestClient, test_user):
        """Should reject wrong password with 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword1",
            },
        )
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Should reject non-existent user with 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "doesnotexist@test.com",
                "password": "TestPass1",
            },
        )
        
        assert response.status_code == 401
    
    def test_login_inactive_user(self, client: TestClient, db, test_user):
        """Should reject deactivated user with 401."""
        from app.models.user import User
        
        # Deactivate the user
        user = db.query(User).filter(User.email == "test@example.com").first()
        user.is_active = False
        db.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass1",
            },
        )
        
        assert response.status_code == 401


class TestAuthMe:
    """Tests for GET /api/v1/auth/me"""
    
    def test_get_current_user(self, client: TestClient, test_user):
        """Should return current user profile."""
        response = client.get(
            "/api/v1/auth/me",
            headers=test_user["headers"],
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["role"] == "admin"
    
    def test_get_me_without_token(self, client: TestClient):
        """Should reject request without token with 401."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_get_me_with_invalid_token(self, client: TestClient):
        """Should reject invalid token with 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        
        assert response.status_code == 401


class TestTokenRefresh:
    """Tests for POST /api/v1/auth/refresh"""
    
    def test_refresh_token_success(self, client: TestClient, test_user):
        """Should return new tokens with valid refresh token."""
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPass1",
            },
        )
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # user can be None on refresh - that's expected
    
    def test_refresh_with_access_token(self, client: TestClient, test_user):
        """Should reject access token used as refresh token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": test_user["token"]},  # Access token, not refresh
        )
        
        assert response.status_code == 401