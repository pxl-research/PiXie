import pytest
from unittest.mock import patch

# =====================
# Auth-related fixtures
# =====================

@pytest.fixture
def mock_user():
    """Mock voor een testgebruiker."""
    return {"username": "testuser", "password": "hashedpassword", "role": "user", "id": 1}


@pytest.fixture
def mock_current_user():
    """Mock voor de huidige gebruiker."""
    return {"username": "philippe", "id": 0, "role": "admin"}


@pytest.fixture
def mock_user_exists():
    """Mock voor de user_exists functie."""
    with patch("app.api.auth.user_exists", return_value=False) as mock:
        yield mock


@pytest.fixture
def mock_add_user_to_db():
    """Mock voor de add_user_to_db functie."""
    with patch("app.api.auth.add_user_to_db", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_verify_password():
    """Mock voor de verify_password functie."""
    with patch("app.api.auth.verify_password", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_create_access_token():
    """Mock voor de create_access_token functie."""
    with patch("app.api.auth.create_access_token", return_value="mocked.jwt.token") as mock:
        yield mock


@pytest.fixture
def mock_decode_access_token(mock_user):
    """Mock voor de decode_access_token functie."""
    with patch("app.api.auth.decode_access_token", return_value={"sub": mock_user["username"], "role": mock_user["role"]}) as mock:
        yield mock

@pytest.fixture
def mock_get_user_by_username(mock_user):
    with patch("app.api.auth.get_user_by_username") as mock:
        mock.side_effect = lambda username: mock_user if username == mock_user["username"] else None
        yield mock


# =========================
# RAG-related fixtures
# =========================

@pytest.fixture
def mock_append_user():
    """Mock voor de append_user functie."""
    with patch("app.blocks_llm_chat_with_rag.append_user") as mock:
        mock.return_value = [{"role": "user", "content": "What is AI?"}]
        yield mock


@pytest.fixture
def mock_append_ai():
    """Mock voor de append_ai functie."""
    with patch("app.blocks_llm_chat_with_rag.append_ai") as mock:
        mock.return_value = (
            "AI-generated answer to 'What is AI?'",
            [
                {"role": "user", "content": "What is AI?"},
                {"role": "assistant", "content": "AI-generated answer to 'What is AI?'"}
            ],
        )
        yield mock


# =========================
# Combined fixture
# =========================

@pytest.fixture
def mock_dependencies(mock_current_user, mock_append_user, mock_append_ai):
    """
    Patch alle benodigde dependencies.

    Args:
        mock_current_user: Mock voor huidige gebruiker.
        mock_append_user: Mock voor append_user.
        mock_append_ai: Mock voor append_ai.

    Yields:
        Gepatchte context voor tests.
    """
    with patch("app.api.auth.decode_access_token", return_value={"sub": "philippe", "role": "admin"}), \
         patch("app.api.llm.get_current_user", return_value=mock_current_user), \
         patch("app.api.auth.get_current_user", return_value=mock_current_user), \
         patch("app.api.auth.oauth2_scheme", return_value="test.mock.token"), \
         patch("app.api.llm.append_user", mock_append_user), \
         patch("app.api.llm.append_ai", mock_append_ai):
        yield