from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .auth import get_current_user
from app.blocks_llm_chat_with_rag import append_user, append_ai
import logging

# Pydantic modellen
class UserInput(BaseModel):
    user_question: str
    collection: str = "pixie"

router = APIRouter()

@router.post("/ask_question")
def ask_question(input_data: UserInput, current_user: dict = Depends(get_current_user)):
    """
    Combineert append_user en append_ai in één stap.

    Args:
        input_data (UserInput): De vraag van de gebruiker en collectie.
        current_user (dict): De huidige ingelogde gebruiker.

    Returns:
        dict: Het antwoord van de AI en bijgewerkte chatgeschiedenis.
    """
    try:
        logging.info(f"User '{current_user['username']}' asked a question: {input_data.user_question}")
        # Voeg de gebruikersvraag toe aan de chatgeschiedenis
        _  = append_user(input_data.user_question, current_user)

        # Genereer een AI-antwoord en voeg dit toe aan de chatgeschiedenis
        response, updated_chat_history = append_ai(input_data.collection, input_data.user_question, current_user)

        return {"response": response, "chat_history": updated_chat_history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")