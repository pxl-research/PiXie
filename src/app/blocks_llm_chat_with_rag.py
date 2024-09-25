from app import llm, chain_builder
from services import document_manager, utils, blob_service
from langchain_community.chat_message_histories import ChatMessageHistory
from typing import List, Dict, Tuple, Generator
import uuid
import json
import os

# Directory where we store the chat history
HISTORY_DIR = "chat_histories"

if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

# Dictionary to store session IDs and their chat histories (Note: may be unused)
session_chains = {}


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
    - str:
        A unique session ID as a string.
    """
    session_id = str(uuid.uuid4())
    print(f"Generated session ID: {session_id}")  # Added for debugging
    return session_id


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
    formatted_history = ""
    for msg in chat_history:
        formatted_history += f"{msg["role"]}: {msg['content']}\n"
    return formatted_history.strip()


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


def append_user(message: str, session_id: str) -> List[Tuple[str, str]]:
    """
    Append a user's message to the chat history and save it.

    Parameters:
    - message: str
        The user's message to append.
    - session_id: str
        The unique session ID for the user.

    Returns:
    - List[Tuple[str, str]]:
        The updated chat history with the user's message added.
    """
    chat_history = load_chat_history(session_id)
    chat_history.append((message, None))
    save_chat_history(session_id, chat_history)
    return chat_history


def append_ai(
    message: str, session_id: str
) -> Generator[Tuple[str, List[Tuple[str, str]]], None, None]:
    """
    Generate an AI response to the user's message, update the chat history, and save it.

    Parameters:
    - message: str
        The user's message to respond to.
    - session_id: str
        The unique session ID for the user.

    Yields:
    - Tuple[str, List[Tuple[str, str]]]:
        A tuple containing an empty string and the updated chat history as the AI response is generated in chunks.
    """
    # Load the chat history for the session
    chat_history = load_chat_history(session_id)
    print(chat_history)

    # Format the chat history for the LLM
    formatted_history = []
    for user_msg, ai_msg in chat_history[
        :-1
    ]:  # Exclude the last message (no AI response yet)
        formatted_history.append({"role": "user", "content": user_msg})
        if ai_msg is not None:
            formatted_history.append({"role": "assistant", "content": ai_msg})

    # Add the current user message
    formatted_history.append({"role": "user", "content": message})

    chat_history_str = format_chat_history(formatted_history)

    # Retrieve and rerank relevant documents
    final_docs = document_manager.retrieve_and_rerank_chunks(message)
    docs = "\n".join([doc.page_content for doc in final_docs])

    # Build the final chain using the updated chain builder
    chain = chain_builder.build_llm_chain(
        chat_history=chat_history_str, docs=docs, question=message
    )

    # Prepare the inputs (placeholders)
    inputs = {"chat_history": chat_history_str, "docs": docs, "question": message}

    # Stream and collect the AI's response
    full_answer = ""
    for chunk, full_answer in _stream_full_answer(chain, inputs):
        chat_history[-1] = (chat_history[-1][0], full_answer)
        yield "", chat_history

    # Optionally add sources to the answer
    if (
        full_answer.strip()
        != "Ik heb niet genoeg informatie om de vraag te beantwoorden."
    ):
        full_answer = _add_sources_to_answer(full_answer, final_docs)

    # Update the chat history with the full answer
    chat_history[-1] = (chat_history[-1][0], full_answer)
    save_chat_history(session_id, chat_history)
    yield "", chat_history


def clear_log(session_id: str) -> List[str]:
    """
    Clear the chat history and delete the associated file for the given session ID.

    Parameters:
    - session_id: str
        The unique session ID for the user.

    Returns:
    - List[str]:
        A list containing two empty strings, used to reset the chat interface.
    """
    history_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(history_file):
        os.remove(history_file)

    return ["", ""]


def _stream_full_answer(
    chain: any, inputs: dict
) -> Generator[Tuple[str, str], None, None]:
    """
    Stream the full answer generated by the chain.

    Parameters:
    - chain: Any
        The chain used to generate the AI response.
    - inputs: dict
        The inputs to the chain, including chat history, documents, and the user's question.

    Yields:
    - Tuple[str, str]:
        A chunk of the AI response and the full answer built up to that point.
    """
    full_answer = ""
    for response in chain.stream(inputs):
        chunk = response.get("text", "")
        full_answer += chunk
        yield chunk, full_answer


def _add_sources_to_answer(answer: str, docs: List[any]) -> str:
    """
    Append source references at the end of the response with hyperlinks to the PDF files in Azure Blob Storage.

    Parameters:
    - answer: str
        The full answer generated by the AI.
    - docs: List[any]
        The list of Document objects used in generating the response.

    Returns:
    - str:
        The answer with the source references appended.
    """
    unique_docs = {doc.metadata["file_name"] for doc in docs}

    if unique_docs:
        sources = "**Sources**:\n" + "\n".join(
            [
                f" - [{doc_name}]({blob_service.generate_blob_url(doc_name)})"
                for doc_name in unique_docs
            ]
        )
        answer += "\n\n" + sources

    return answer
