from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)

def test_ask_question(mock_dependencies):
    """Test de ask_question route."""
    headers = {"Authorization": "Bearer test.mock.token"}
    data = {
        "user_question": "What is AI?",
        "collection": "pixie"
    }

    # Maak de API-aanroep
    response = client.post("/llm/ask_question", json=data, headers=headers)

    # Valideer de response
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    assert response.json() == {
        "response": "AI-generated answer to 'What is AI?'",
        "chat_history": [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI-generated answer to 'What is AI?'"}
        ]
    }