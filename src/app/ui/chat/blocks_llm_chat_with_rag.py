from typing import List, Dict, Tuple, Optional, Any, AsyncGenerator
from services.chat_history import chat_history_manager
from services.agent_service import execute_agent_for_avatar, execute_agent
import logging


logger = logging.getLogger(__name__)


def append_user(
    message: str, user_info: Optional[Dict[str, Any]]
) -> List[Tuple[str, str]]:
    """
    Append a user's message to the chat history and save it.

    Parameters:
    - message: str
        The message from the user to append to the chat history.
    - user_info: Optional[Dict[str, Any]]
        A dictionary containing user information, including the user ID.

    Returns:
    - List[Tuple[str, str]]: The updated chat history list of tuples, where each tuple contains the user's message
      and the AI response (or None if no response yet).
    """
    try:
        user_id = user_info["id"] if user_info else 0
        session_id = user_info.get("session_id", "0") if user_info else "0"

        logger.debug(
            f"Appending user message - user_id: {user_id}, session_id: {session_id}"
        )

        chat_history = chat_history_manager.get_chat_history(
            user_id, limit=10, session_id=session_id
        )

        chat_history_manager.save_chat_history(
            user_id, message, None, session_id=session_id
        )

        chat_history = chat_history_manager.add_message_to_chat_history(
            chat_history, "user", message
        )

        logger.info(
            f"User message appended successfully - user_id: {user_id}, message_length: {len(message)}"
        )
        return chat_history

    except Exception as e:
        logger.error(
            f"Error appending user message - user_id: {user_id if 'user_id' in locals() else 'unknown'}: {e}",
            exc_info=True,
        )
        raise


async def append_ai(
    collection_name: str,
    message: str,
    user_info: Optional[Dict[str, Any]],
    mcp_state: Optional[Any] = None,
) -> AsyncGenerator[Tuple[str, List[Tuple[str, str]]], None]:
    """
    Generate an AI response to the user's message, update the chat history, and save it.

    Parameters:
    ----------
    collection_name : str
      The name of the document collection to search for relevant information.
    message : str
      The user's message that requires an AI response.
    user_info : Optional[Dict[str, Any]]
      A dictionary containing user information, including the user ID.
      If None, the function will use a default/anonymous user context.
    mcp_state : Optional[Any]
      The state object for the MCP agent.

    Returns:
    -------
    AsyncGenerator[Tuple[str, List[Tuple[str, str]]], None]
      A tuple containing:
      - An empty string (used for clearing the UI's input field)
      - The updated chat history as a list of (role, message) tuples
      - A Gradio update command to hide the loading spinner

    Note:
    -----
    This function retrieves the chat history, formats it for the LLM,
    uses execute_agent to generate a response with RAG capabilities,
    then updates and saves the chat history with the AI's response.
    """
    try:
        user_id = (
            user_info["id"] if user_info else 0
        )  # Default to 0 for anonymous users
        session_id = user_info.get("session_id", "0") if user_info else "0"

        logger.debug(
            f"Starting AI response generation - user_id: {user_id}, session_id: {session_id}, collection: {collection_name}"
        )

        chat_history = chat_history_manager.get_chat_history(
            user_id, limit=9, session_id=session_id
        )
        formatted_history = chat_history_manager.format_chat_history_for_llm(
            chat_history[-5:] if len(chat_history) > 5 else chat_history
        )

        logger.debug(
            f"Chat history retrieved - user_id: {user_id}, history_length: {len(chat_history)}"
        )

        final_answer = ""
        async for content, metadata_title in execute_agent(
            message, formatted_history, collection_name
        ):
            final_answer = content
            chat_history = chat_history_manager.replace_last_message_in_chat_history(
                chat_history, "assistant", content, {"title": metadata_title}
            )
            yield "", chat_history

        chat_history_manager.save_chat_history(
            user_id, None, final_answer, session_id=session_id
        )

        logger.info(
            f"AI response generated successfully - user_id: {user_id}, response_length: {len(final_answer)}"
        )
        yield "", chat_history

    except Exception as e:
        logger.error(
            f"Error generating AI response - user_id: {user_id if 'user_id' in locals() else 'unknown'}, collection: {collection_name}: {e}",
            exc_info=True,
        )
        raise


def clear_log(user_info: Optional[Dict[str, Any]]) -> List[str]:
    """
    Clear the chat history and delete the associated file for the given user.

    Parameters:
    - user_info: Optional[Dict[str, Any]]
        A dictionary containing user information, including the user ID.

    Returns:
    - List[str]: An empty list containing two empty strings, used to reset the chat interface.
    """
    try:
        user_id = user_info["id"] if user_info else 0
        session_id = user_info.get("session_id", "0") if user_info else "0"

        logger.debug(
            f"Clearing chat history - user_id: {user_id}, session_id: {session_id}"
        )

        chat_history_manager.delete_chat_history(str(user_id), session_id=session_id)

        logger.info(
            f"Chat history cleared successfully - user_id: {user_id}, session_id: {session_id}"
        )
        return ["", ""]

    except Exception as e:
        logger.error(
            f"Error clearing chat history - user_id: {user_id if 'user_id' in locals() else 'unknown'}: {e}",
            exc_info=True,
        )
        raise


async def append_ai_for_api(
    message: str,
    user_info: Optional[Dict[str, Any]],
    collection_name: str,
) -> str:
    """
    Process message for API use and return final answer with chat history support.
    """
    try:
        # Get user info like in append_ai
        user_id = user_info["id"] if user_info else 0
        session_id = user_info.get("session_id", "0") if user_info else "0"

        logger.debug(
            f"Processing API message - user_id: {user_id}, session_id: {session_id}, collection: {collection_name}"
        )

        # Get and format chat history like in append_ai
        chat_history = chat_history_manager.get_chat_history(
            user_id, limit=19, session_id=session_id
        )
        formatted_history = chat_history_manager.format_chat_history_for_llm(
            chat_history[-10:] if len(chat_history) > 10 else chat_history
        )

        logger.debug(
            f"Chat history retrieved for API - user_id: {user_id}, history_length: {len(chat_history)}"
        )

        # Call the avatar function
        response = await execute_agent_for_avatar(
            message, formatted_history, collection_name
        )

        # Save the AI response to chat history like in append_ai
        chat_history_manager.save_chat_history(
            user_id, None, response, session_id=session_id
        )

        logger.info(
            f"API response generated successfully - user_id: {user_id}, response_length: {len(response)}"
        )
        return response

    except Exception as e:
        logger.error(
            f"Error in API message processing - user_id: {user_id if 'user_id' in locals() else 'unknown'}, collection: {collection_name}: {e}",
            exc_info=True,
        )
        return "Er ging iets mis bij het verwerken van je vraag. Probeer het opnieuw."
