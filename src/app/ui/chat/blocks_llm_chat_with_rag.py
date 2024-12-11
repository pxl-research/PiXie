from typing import List, Dict, Tuple, Optional, Any
import os

from services.chat_history import chat_history_manager
from services import source_processing
from services.oracle.graph_runner import initialize_graph, compile_graph, execute_graph


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
    print("Echte append_user functie")
    chat_history = chat_history_manager.get_chat_history(user_id, limit=10)
    chat_history_manager.save_chat_history(user_id, message, None)
    chat_history = chat_history_manager.add_message_to_chat_history(
        chat_history, "user", message
    )
    return chat_history


def append_ai(
    collection_name: str, message: str, user_info: Optional[Dict[str, Any]]
) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Generate an AI response to the user's message, update the chat history, and save it.

    Parameters:
    - collection_name: str
        The name of the collection to retrieve documents from.
    - message: str
        The user's message to which the AI should respond.
    - user_info: Optional[Dict[str, Any]]
        A dictionary containing user information, including the user ID.

    Returns:
    - Tuple[str, List[Tuple[str, str]]]: The final response text for the textbox and the updated chat history for the chatbot.
    """
    user_id = user_info["id"] if user_info else None

    chat_history = chat_history_manager.get_chat_history(user_id, limit=9)
    chat_history_for_llm = chat_history_manager.get_chat_history(
        user_id=user_id, limit=5
    )
    formatted_history = chat_history_manager.format_chat_history_for_llm(
        chat_history_for_llm
    )

    graph = initialize_graph()
    compiled_oracle_graph = compile_graph(graph)

    answer, sources = execute_graph(
        compiled_oracle_graph,
        {
            "input": message,
            "chat_history": formatted_history,
            "collection_name": collection_name,
        },
    )

    sources_list = source_processing.process_sources(sources.strip()) if sources else []

    # Format the final answer with enriched sources
    final_answer = source_processing.format_final_answer(
        answer.strip(), source_processing.enrich_sources(sources_list)
    )
    chat_history = chat_history_manager.add_message_to_chat_history(
        chat_history, "assistant", final_answer
    )

    chat_history_manager.save_chat_history(user_id, None, final_answer)
    return "", chat_history


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
