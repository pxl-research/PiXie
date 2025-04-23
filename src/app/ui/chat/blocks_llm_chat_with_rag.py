from typing import List, Dict, Tuple, Optional, Any
from services.chat_history import chat_history_manager
from services.agent_service import execute_agent


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
    user_id = user_info["id"] if user_info else None
    chat_history = chat_history_manager.get_chat_history(user_id, limit=10)
    chat_history_manager.save_chat_history(user_id, message, None)
    chat_history = chat_history_manager.add_message_to_chat_history(
        chat_history, "user", message
    )
    return chat_history


async def append_ai(
    collection_name: str, message: str, user_info: Optional[Dict[str, Any]]
) -> Tuple[str, List[Tuple[str, str]]]:
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

    Returns:
    -------
    Tuple[str, List[Tuple[str, str]]]
      A tuple containing:
      - An empty string (used for clearing the UI's input field)
      - The updated chat history as a list of (role, message) tuples

    Note:
    -----
    This function retrieves the chat history, formats it for the LLM,
    uses execute_agent to generate a response with RAG capabilities,
    then updates and saves the chat history with the AI's response.
    """
    user_id = user_info["id"] if user_info else None

    chat_history = chat_history_manager.get_chat_history(user_id, limit=9)
    formatted_history = chat_history_manager.format_chat_history_for_llm(
        chat_history_manager.get_chat_history(user_id=user_id, limit=5)
    )

    final_answer = ""
    # Hier itereren we over elke yield van execute_agent.
    async for content, metadata in execute_agent(
        message, formatted_history, collection_name
    ):
        # We kunnen ervoor kiezen om het laatste update als eindantwoord te gebruiken.
        final_answer = content

        chat_history = chat_history_manager.replace_last_message_in_chat_history(
            chat_history, "assistant", content, metadata
        )

        yield "", chat_history

    chat_history_manager.save_chat_history(user_id, None, final_answer)
    yield "", chat_history


def clear_log(user_info: Optional[Dict[str, Any]]) -> List[str]:
    """
    Clear the chat history and delete the associated file for the given user.

    Parameters:
    - user_info: Optional[Dict[str, Any]]
        A dictionary containing user information, including the user ID.

    Returns:
    - List[str]: An empty list containing two empty strings, used to reset the chat interface.
    """
    user_id = user_info["id"] if user_info else None
    chat_history_manager.delete_chat_history(user_id)
    return ["", ""]
