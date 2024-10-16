from typing import List, Dict, Tuple
import os
import json


# Directory where we store the chat history
HISTORY_DIR = "chat_histories"

if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)


def save_chat_history(session_id: str, history: List[Tuple[str, str]]) -> None:
    """
    Save the chat history for a given session ID.

    Parameters:
    - session_id: str
        The unique session ID for the user.
    - history: List[Tuple[str, str]]
        The chat history to save, as a list of tuples (user_message, ai_response).

    Returns:
    - None
    """
    history_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
    with open(history_file, "w") as f:
        json.dump(history, f)


def load_chat_history(session_id: str) -> List[Tuple[str, str]]:
    """
    Load the chat history for a given session ID.

    Parameters:
    - session_id: str
        The unique session ID for the user.

    Returns:
    - List[Tuple[str, str]]:
        The chat history as a list of tuples (user_message, ai_response).
        Returns an empty list if no history is found.
    """
    history_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return json.load(f)
    return []


def format_chat_history(chat_history: List[Dict[str, str]]) -> str:
    """
    Format the chat history into a string suitable for the prompt.

    Parameters:
    - chat_history: List[Dict[str, str]]
        The chat history formatted as a list of messages with 'role' and 'content'.

    Returns:
    - str:
        The formatted chat history as a string, with roles and messages.
    """
    return "\n".join(f"{msg['role']}: {msg['content']}" for msg in chat_history).strip()


def delete_chat_history(session: Dict[str, any]) -> None:
    """
    Delete the chat history when the session ends.

    Parameters:
    - session: Dict[str, any]
        The session state containing the session ID.

    Returns:
    - None
    """
    # Access the session state
    if "session_id" in session:
        session_id = session["session_id"]
        history_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
        if os.path.exists(history_file):
            os.remove(history_file)
            print(f"Chat history for session {session_id} has been deleted.")


def get_chat_history(session_id: str) -> List[Tuple[str, str]]:
    """
    Retrieve the chat history for a given session ID.

    Parameters:
    - session_id: str
        The unique session ID for the user.

    Returns:
    - List[Tuple[str, str]]:
        The chat history as a list of tuples (user_message, ai_response).
    """
    return load_chat_history(session_id)


def strip_sources(text: str) -> str:
    """
    Strip everything after the keyword 'Bronnen:' from the given text.

    Parameters:
    - text: str
        The input text from which to remove sources.

    Returns:
    - str: The text with any content after 'Bronnen:' removed. If 'Bronnen:' is not found, the original text is returned, stripped of any leading or trailing whitespace.
    """
    keyword_position = text.find("Bronnen:")
    return text[:keyword_position].strip() if keyword_position != -1 else text.strip()


def format_chat_history_for_llm(chat_history, message):
    """
    Format the chat history for processing by a Language Learning Model (LLM).

    This function converts a list of user and AI messages into a structured format compatible with an LLM. It processes each message, adds the user's new message, and removes any sources from AI messages by calling `strip_sources`.

    Parameters:
    - chat_history: list
        A list of tuples, where each tuple contains:
          - str: The user's message
          - str or None: The AI's response, or None if there is no response yet
    - message: str
        The latest message from the user to be appended to the formatted chat history.

    Returns:
    - list: A formatted list of dictionaries, where each dictionary contains:
          - 'role': str, specifying either 'user' or 'assistant'
          - 'content': str, containing the message content with sources removed for AI responses
    """
    formatted_history = []
    for user_msg, ai_msg in chat_history[:-1]:
        formatted_history.append({"role": "user", "content": user_msg})
        if ai_msg is not None:
            formatted_history.append(
                {"role": "assistant", "content": strip_sources(ai_msg)}
            )
    formatted_history.append({"role": "user", "content": message})
    return formatted_history
