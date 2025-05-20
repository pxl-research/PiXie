from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.auth import get_current_user
from app.ui.chat.blocks_llm_chat_with_rag import append_user, append_ai_for_api
import logging


# Pydantic modellen
class UserInput(BaseModel):
    user_question: str
    session_id: int = 0
    collection: str = "pixie"


class AIResponse(BaseModel):
    response: str


chat_router = APIRouter()


@chat_router.post(
    "/chat",
    response_model=AIResponse,
    summary="Submit a question to the AI with RAG and session support",
    description=(
        "Adds a user question to the chat history and generates a response "
        "using retrieval-augmented generation (RAG) from the specified collection. "
        "Supports session-based history using session_id."
    ),
    tags=["Chat"],
)
async def chat(input_data: UserInput, current_user: dict = Depends(get_current_user)):
    """
    Combineert append_user en append_ai in één stap.

    Args:
        input_data (UserInput): De vraag van de gebruiker en collectie.
        current_user (dict): De huidige ingelogde gebruiker.

    Returns:
        dict: Het antwoord van de AI en bijgewerkte chatgeschiedenis.
    """
    try:
        current_user["session_id"] = input_data.session_id
        logging.info(
            f"User '{current_user['username']}' asked a question: {input_data.user_question}"
        )
        # Voeg de gebruikersvraag toe aan de chatgeschiedenis
        append_user(input_data.user_question, current_user)

        # Genereer een AI-antwoord en voeg dit toe aan de chatgeschiedenis
        response: str = await append_ai_for_api(
            input_data.collection, input_data.user_question, current_user
        )

        return {"response": response}
    except Exception as e:
        logging.exception(
            f"Error processing chat request for user '{current_user['username']}': {e}"
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")
