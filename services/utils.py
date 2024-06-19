import hashlib
from pandas import read_csv, DataFrame, concat, Timestamp
import json
import os
from langchain_core.messages import AIMessage, HumanMessage, messages_from_dict, messages_to_dict

history_path = "../assets/helper/chat_history.json"


def compute_hash(file_path):
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read and update hash in chunks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def is_doc_up_to_date_in_list(file_hash, doc_list_path):
    doc_list = read_csv(doc_list_path)
    if doc_list.empty:
        return False
    return file_hash in doc_list["file_hash"].values


def is_doc_in_list(file_name, doc_list_path):
    doc_list = read_csv(doc_list_path)
    if doc_list.empty:
        return False
    return file_name in doc_list["file_name"].values


def read_template(file_path):
    with open(file_path, "r") as file:
        template = file.read()
    return template


def add_to_doc_list(
    doc_list_path: str, file_name: str, file_hash: str, delete: bool = False
):
    """
    Adds a document to the document list.
    """
    doc_list = read_csv(doc_list_path)
    new_row = DataFrame(
        {
            "file_name": [file_name],
            "file_hash": [file_hash],
            "last_updated": [Timestamp.now()],
        }
    )
    doc_list = concat([doc_list, new_row], ignore_index=True)
    doc_list.to_csv(doc_list_path, index=False)


def get_doc_list(doc_list_path: str):
    """
    Returns the document list.
    """
    return read_csv(doc_list_path)


def get_chat_history(history_path: str) -> list:
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            chat_history_json = json.load(f)
        retrieved_messages = messages_from_dict(chat_history_json)
    else:
        retrieved_messages = []
    return retrieved_messages


def save_chat_history(history_path: str, question: str, response: str):

    retrieved_messages = get_chat_history(history_path)

    retrieved_messages.append(HumanMessage(content=question))
    retrieved_messages.append(AIMessage(content=response))

    # Save the entire chat history back to the JSON file
    ingest_to_db = messages_to_dict(retrieved_messages)

    with open(history_path, "w") as f:
        json.dump(ingest_to_db, f)
