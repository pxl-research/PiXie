from app import llm, tabular_vector_store
from typing import List, Dict, Tuple, Optional, Any
import os

from services.chat_history import chat_history_manager
from services import source_processing
from services.database.document_db_operations import get_summaries_by_collection
from services.prompt_manager import get_agent_system_prompt, get_tool_description
from services.mcp_tools.tool_config import get_mcp_tool_configurations

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

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

    This asynchronous function orchestrates the entire AI response generation pipeline:
    1. Retrieves and formats the chat history
    2. Initializes tool connections through MultiServerMCPClient
    3. Gathers document summaries from vector stores
    4. Creates a customized system prompt
    5. Executes the agent to generate a response
    6. Updates and saves the chat history

    Parameters:
    ----------
    collection_name : str
        The name of the document collection to search within for relevant information.
    message : str
        The user's message that requires an AI response.
    user_info : Optional[Dict[str, Any]]
        A dictionary containing user information, including the user ID.
        If None, the function will use a default/anonymous user context.

    Returns:
    -------
    Tuple[str, List[Tuple[str, str]]]
        A tuple containing:
        - An empty string (used for the UI's textbox)
        - The updated chat history as a list of (role, message) tuples

    Note:
    -----
    This function leverages various tools through the MCP client including RAG search,
    tabular database queries, weather information, and other specialized tools configured
    in the mcp_tool_configurations. The response generation is delegated to the execute_agent
    function which handles tool selection and response formatting.
    """
    user_id = user_info["id"] if user_info else None

    chat_history = chat_history_manager.get_chat_history(user_id, limit=9)
    formatted_history = chat_history_manager.format_chat_history_for_llm(
        chat_history_manager.get_chat_history(user_id=user_id, limit=5)
    )

    async with MultiServerMCPClient(get_mcp_tool_configurations()) as client:
        summaries = get_summaries_by_collection(collection_name)
        tabular_summaries = tabular_vector_store.get_summaries_by_collection(
            collection_name
        )

        custom_prompt = get_agent_system_prompt(summaries, tabular_summaries)

        final_answer, _ = await execute_agent(
            client, message, custom_prompt, formatted_history, collection_name
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
