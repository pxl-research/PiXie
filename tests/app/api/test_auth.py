import pytest
from fastapi.testclient import TestClient
from app.api.auth import router, register, RegisterUser, get_current_user
from fastapi import HTTPException
from unittest.mock import patch

# Mock de TestClient met de router
client = TestClient(router)


# Test de /token route
def test_login(mock_get_user_by_username, mock_verify_password, mock_create_access_token):
    response = client.post("/token", data={"username": "testuser", "password": "correctpassword"})

    assert response.status_code == 200
    assert response.json() == {"access_token": "mocked.jwt.token", "token_type": "bearer"}


# Test de /register route
def test_register(mock_user_exists, mock_add_user_to_db):
    response = client.post("/register", json={"username": "newuser", "password": "newpassword", "role": "user"})

    assert response.status_code == 200
    assert response.json() == {"message": "User 'newuser' successfully registered"}


def test_register_user_exists():
    with patch("app.api.auth.user_exists", return_value=True):
        with pytest.raises(HTTPException) as excinfo:
            register(RegisterUser(username="existinguser", password="password", role="user"))

        assert excinfo.value.status_code == 400
        assert excinfo.value.detail == "User already exists"


# Test de /me route
def test_get_current_user(mock_decode_access_token, mock_get_user_by_username, mock_user):
    headers = {"Authorization": "Bearer mocked.jwt.token"}
    response = client.get("/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"username": mock_user["username"], "role": mock_user["role"], "id": mock_user["id"]}


# Test de /me route met een ongeldig token
def test_get_current_user_invalid_token():
    with patch("app.api.auth.decode_access_token", side_effect=HTTPException(status_code=401, detail="Invalid token")) as mock_decode_access_token:
        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token="invalid.jwt.token")

        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "Invalid token"
        mock_decode_access_token.assert_called_once_with("invalid.jwt.token")


# Test de /me route met een geldig token, maar een niet-bestaande gebruiker
def test_get_current_user_user_not_found():
    with patch("app.api.auth.decode_access_token", return_value={"sub": "unknownuser"}) as mock_decode_access_token, \
         patch("app.api.auth.get_user_by_username", return_value=None) as mock_get_user_by_username:

        with pytest.raises(HTTPException) as excinfo:
            get_current_user(token="valid.jwt.token")

        assert excinfo.value.status_code == 401
        assert excinfo.value.detail == "User not found"
        mock_decode_access_token.assert_called_once_with("valid.jwt.token")
        mock_get_user_by_username.assert_called_once_with(username="unknownuser")