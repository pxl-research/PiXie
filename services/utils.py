import hashlib
import json
import os
import logging
from pandas import read_csv, DataFrame, concat, Timestamp
from typing import List, Optional
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    messages_from_dict,
    messages_to_dict,
)
from langchain_community.chat_message_histories import ChatMessageHistory

# Constants
HISTORY_PATH = "../assets/helper/chat_history.json"
DOC_LIST_PATH = "../assets/helper/doc_list.csv"

def compute_hash(file_path: str) -> str:
    """
    Compute the SHA-256 hash of a file.

    Parameters:
    - file_path: str
        The path to the file to be hashed.

    Returns:
    - str: The computed SHA-256 hash of the file.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def is_doc_up_to_date_in_list(file_hash: str, doc_list_path: str) -> bool:
    """
    Check if a document with a given hash is up-to-date in the document list.

    Parameters:
    - file_hash: str
        The hash of the document to check.
    - doc_list_path: str
        The path to the document list CSV file.

    Returns:
    - bool: True if the document is up-to-date, False otherwise.
    """
    doc_list = read_csv(doc_list_path)
    if doc_list.empty:
        return False
    return file_hash in doc_list["file_hash"].values


def is_doc_in_list(file_name: str, doc_list_path: str) -> bool:
    """
    Check if a document with a given name exists in the document list.

    Parameters:
    - file_name: str
        The name of the document to check.
    - doc_list_path: str
        The path to the document list CSV file.

    Returns:
    - bool: True if the document exists in the list, False otherwise.
    """
    doc_list = read_csv(doc_list_path)
    if doc_list.empty:
        return False
    return file_name in doc_list["file_name"].values


def read_template(file_path: str) -> str:
    """
    Read and return the content of a template file.

    Parameters:
    - file_path: str
        The path to the template file.

    Returns:
    - str: The content of the template file.
    """
    with open(file_path, "r") as file:
        return file.read()


def add_to_doc_list(doc_list_path: str, file_name: str, file_hash: str, delete: bool = False) -> None:
    """
    Add a document to the document list or update the last updated timestamp.

    Parameters:
    - doc_list_path: str
        The path to the document list CSV file.
    - file_name: str
        The name of the document to add or update.
    - file_hash: str
        The hash of the document.
    - delete: bool, optional
        If True, delete the old document entry before adding the new one (default is False).

    Returns:
    - None
    """
    doc_list = read_csv(doc_list_path)
    if delete:
        doc_list = doc_list[doc_list["file_name"] != file_name]
    
    new_row = DataFrame({
        "file_name": [file_name],
        "file_hash": [file_hash],
        "last_updated": [Timestamp.now()],
    })
    
    doc_list = concat([doc_list, new_row], ignore_index=True)
    doc_list.to_csv(doc_list_path, index=False)
    logging.info(f"Document {file_name} added to the document list.")


def remove_from_doc_list(doc_list_path: str, file_name: str) -> None:
    """
    Remove a document from the document list.

    Parameters:
    - doc_list_path: str
        The path to the document list CSV file.
    - file_name: str
        The name of the document to remove.

    Returns:
    - None
    """
    doc_list = read_csv(doc_list_path)
    doc_list = doc_list[doc_list.file_name != file_name]
    doc_list.to_csv(doc_list_path, index=False)
    logging.info(f"Document {file_name} removed from the document list.")


def get_doc_list(doc_list_path: str) -> DataFrame:
    """
    Return the document list as a DataFrame.

    Parameters:
    - doc_list_path: str
        The path to the document list CSV file.

    Returns:
    - DataFrame: A DataFrame containing the document list.
    """
    return read_csv(doc_list_path)


def get_chat_history(history_path: str = HISTORY_PATH, limit: Optional[int] = None) -> ChatMessageHistory:
    """
    Retrieve chat history from the given path. If a limit is provided, return only the most recent messages.

    Parameters:
    - history_path: str, optional
        The file path to the JSON file where chat history is stored (default is HISTORY_PATH).
    - limit: Optional[int], optional
        The number of most recent messages to return. If None, return all messages.

    Returns:
    - ChatMessageHistory: A ChatMessageHistory object containing the messages.
    """
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            chat_history_json = json.load(f)
        messages = messages_from_dict(chat_history_json)
    else:
        messages = []

    if limit is not None:
        messages = messages[-limit:]

    return ChatMessageHistory(messages=messages)


def save_chat_history(question: str, response: str, history_path: str = HISTORY_PATH) -> None:
    """
    Append a new interaction to the chat history and save it to the specified JSON file.

    Parameters:
    - history_path: str
        The file path to the JSON file where chat history is stored.
    - question: str
        The question or message provided by the user.
    - response: str
        The response generated by the AI.

    Returns:
    - None
    """
    chat_history = get_chat_history(history_path)

    chat_history.add_message(HumanMessage(content=question))
    chat_history.add_message(AIMessage(content=response))

    chat_history_dict = messages_to_dict(chat_history.messages)

    with open(history_path, "w") as f:
        json.dump(chat_history_dict, f, indent=2)
    logging.info("Chat history updated and saved.")