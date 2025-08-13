from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.api.auth import get_current_user
from app.ui.chat.blocks_llm_chat_with_rag import append_user, append_ai_for_api
from services.conversation_logger import conversation_logger
import logging
import time
from services.init_services import get_services
from services.conversation_loop import ConversationLoop


# Pydantic modellen
class UserInput(BaseModel):
    user_question: str
    session_id: str = "0"
    collection: str = "pixie"


class AIResponse(BaseModel):
    response: str


chat_router = APIRouter()
services = get_services()
conversation_loop = ConversationLoop(llm=services["llm"], collection_name="auva")


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
async def chat(
    input_data: UserInput,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Combineert append_user en append_ai in één stap.

    Args:
        input_data (UserInput): De vraag van de gebruiker en collectie.
        request (Request): FastAPI request object voor client info.
        current_user (dict): De huidige ingelogde gebruiker.

    Returns:
        dict: Het antwoord van de AI en bijgewerkte chatgeschiedenis.
    """
    start_time = time.time()
    print("Er komt een vraag binnen")
    print(f"User question: {input_data.user_question}")

    try:
        print(f"Session ID: {input_data.session_id}")
        print(f"Old session ID: {services['session_id']}")
        if input_data.session_id != services["session_id"]:
            print("Starting new conversation loop")
            services["session_id"] = input_data.session_id
            services["conversation_loop"] = ConversationLoop(
                llm=services["llm"], collection_name="auva"
            )

        current_user["session_id"] = input_data.session_id
        user_id = current_user.get("id", 0)
        session_id = input_data.session_id

        # Haal client informatie op
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        # Start sessie in conversation logger
        conversation_logger.start_session(
            session_id=session_id,
            user_id=user_id,
            client_info={
                "ip": client_ip,
                "user_agent": user_agent,
                "collection": input_data.collection,
            },
        )

        # Log gebruikersvraag
        conversation_logger.log_user_question(
            session_id=session_id,
            user_id=user_id,
            question=input_data.user_question,
            user_ip=client_ip,
            user_agent=user_agent,
            metadata={
                "collection_requested": input_data.collection,
                "username": current_user.get("username", "unknown"),
            },
        )

        logging.info(
            f"User '{current_user['username']}' asked a question: {input_data.user_question}"
        )

        # Voeg de gebruikersvraag toe aan de chatgeschiedenis
        append_user(input_data.user_question, current_user)

        # Genereer een AI-antwoord en voeg dit toe aan de chatgeschiedenis
        _, response = services["conversation_loop"].send(input_data.user_question)

        # await append_ai_for_api(
        #     input_data.user_question, current_user, input_data.collection
        # )

        # Bereken verwerkingstijd
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log AI response
        conversation_logger.log_ai_response(
            session_id=session_id,
            user_id=user_id,
            response=response,
            processing_time_ms=processing_time_ms,
            collection_used=input_data.collection,
            metadata={
                "username": current_user.get("username", "unknown"),
                "response_length": len(response),
            },
        )

        return {"response": response}

    except Exception as e:
        # Log error event
        if "session_id" in locals() and "user_id" in locals():
            conversation_logger.log_error_event(
                session_id=session_id,
                user_id=user_id,
                error_message=str(e),
                error_details=f"Error in chat endpoint: {type(e).__name__}",
                metadata={
                    "username": current_user.get("username", "unknown"),
                    "question": input_data.user_question,
                    "collection": input_data.collection,
                },
            )

        logging.exception(
            f"Error processing chat request for user '{current_user['username']}': {e}"
        )
        raise HTTPException(status_code=500, detail="Internal Server Error")
