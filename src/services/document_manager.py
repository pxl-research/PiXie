import os
import shutil
import logging
import pandas as pd
from werkzeug.utils import secure_filename
from services import utils, blob_service
from typing import List, Tuple, Optional
from app import document_loader, splitter, vector_store, reranker
from database.document_db_operations import (
    is_doc_up_to_date_in_list,
    is_doc_in_list,
    add_to_doc_list,
    remove_from_doc_list,
    get_doc_list,
)
from page_numbering import text_chunks_to_page_numbers
import gradio as gr

UPLOAD_FOLDER = "./uploads"


def retrieve_and_rerank_chunks(
    collection_name: str, message: str, top_k: int = 15, final_k: int = 5
) -> List:
    """
    Retrieve and optionally rerank document chunks based on the input message.

    This function retrieves the top `top_k` chunks relevant to the input `message` from the vector store.
    If a reranker is available, it reranks these chunks and returns the top `final_k` chunks. Otherwise,
    it simply returns the first `final_k` chunks from the retrieved list.

    Parameters:
        collection_name (str): The name of the collection to retrieve document chunks from.
        message (str): The input message used to retrieve relevant document chunks.
        top_k (int, optional): The number of top chunks to retrieve initially. Defaults to 15.
        final_k (int, optional): The number of chunks to return after reranking. Defaults to 5.

    Returns:
        List: A list of the final selected document chunks.
    """
    top_chunks = vector_store.retrieve_top_chunks(collection_name, message, top_k)

    if reranker is not None:
        final_chunks = reranker.rerank(message, top_chunks, final_k)
        logging.info(f"Chunks have been reranked for the message: {message}")
    else:
        final_chunks = top_chunks[:final_k]
        logging.info(
            f"No reranker available. Returning top {final_k} chunks for the message: {message}"
        )

    return final_chunks


def add_document(collection_name: str, file_path: str) -> Optional[str]:
    """
    Handle the process of uploading, securing the file name, loading, splitting,
    and adding a document to the vector store.

    This function secures the filename, copies the file to the upload folder, computes its hash,
    checks if the document is up-to-date, and if not, processes the document by loading, splitting,
    and adding it to the vector store. It also uploads the file to Azure Blob Storage and updates
    the document list accordingly.

    Parameters:
        collection_name (str): The name of the collection to add the document to.
        file_path (str): The path of the file to handle.

    Returns:
        Optional[str]: The secure file name if added or updated, otherwise None.
    """
    _prepare_upload_folder()

    # Secure and copy the file to the upload folder
    file_name = os.path.basename(file_path)
    secure_file_name = secure_filename(file_name)
    temp_file_path = os.path.join(UPLOAD_FOLDER, secure_file_name)

    shutil.copy(file_path, temp_file_path)
    logging.info(f"Temporary file {temp_file_path} has been saved.")

    try:
        # Compute the file hash
        file_hash = utils.compute_hash(temp_file_path)

        # Check if the document is already up-to-date
        if is_doc_up_to_date_in_list(file_hash, collection_name):
            logging.info(f"File {secure_file_name} is already up-to-date.")
            return None

        delete = is_doc_in_list(secure_file_name, collection_name)

        # Load, split, and add the document to the vector store
        document = document_loader.load_document(temp_file_path)
        chunks = splitter.split(document)

        # Extract text from chunks
        text_chunks = [chunk.page_content for chunk in chunks]

        # Map text chunks to page numbers
        page_numbers_list = text_chunks_to_page_numbers(temp_file_path, text_chunks)

        # Add page numbers to chunks metadata (only if page numbers exist)
        for chunk, page_numbers in zip(chunks, page_numbers_list):
            if page_numbers is not None:
                chunk.metadata["page_numbers"] = page_numbers

        vector_store.add_document(collection_name, secure_file_name, chunks)

        # Update the document list
        add_to_doc_list(secure_file_name, file_hash, collection_name, delete)

        # Upload the file to Azure Blob Storage
        blob_service.upload_blob(temp_file_path, secure_file_name)
        logging.info(
            f"Document {secure_file_name} has been uploaded to Azure Blob Storage."
        )

        logging.info(
            f"Document {secure_file_name} has been added to the vector store and the document list."
        )

        return secure_file_name

    finally:
        # Ensure the temporary file is removed after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logging.debug(f"Temporary file {temp_file_path} has been removed.")


def add_documents(
    file_paths: List[str], collection_name: str = "pixie"
) -> List[List[str]]:
    """
    Add multiple documents to the system and retrieve the updated document list.

    This function iterates over a list of file paths, adding each document to the document store
    by invoking the `add_document` function. After all documents are added, it retrieves the updated
    list of document collections by calling `list_documents`.

    Parameters:
        file_paths (List[str]): A list of file paths representing the documents to be added.

    Returns:
        List[List[str]]: An updated list of document collections, where each inner list contains
        information about a single document.
    """
    for file_path in file_paths:
        add_document(collection_name, file_path)

    # Get the updated list of document collections
    df_files = list_documents(collection_name)
    return df_files


def remove_document(
    selected_file: str, collection_name: str = "pixie"
) -> Tuple[str, List[List[str]]]:
    """
    Remove a document from the vector store, the collection list, and Azure Blob Storage.

    This function deletes the specified document from the vector store, removes it from the
    document list, and deletes it from Azure Blob Storage. It then retrieves the updated
    list of documents and determines whether the delete button should remain interactive.

    Parameters:
        selected_file (str): The name of the file to remove.

    Returns:
        Tuple[str, pd.DataFrame, gr.Update]:
            - feedback_text (str): A message indicating the result of the deletion.
            - files_df (pd.DataFrame): The updated DataFrame of files.
            - delete_button_state (gr.Update): The updated state of the delete button's interactivity.
    """
    if selected_file:
        try:
            logging.info(f"Removing document: {selected_file}")
            vector_store.delete_document(collection_name, selected_file)
            success = remove_from_doc_list(selected_file, collection_name)
            blob_service.delete_blob(selected_file)
            if success:
                feedback_text = f"File '{selected_file}' has been successfully removed."
            else:
                feedback_text = f"Could not remove file '{selected_file}'."
        except Exception as e:
            logging.error(f"Failed to remove document {selected_file}: {e}")
            feedback_text = f"An error occurred while removing the file: {str(e)}"
    else:
        feedback_text = "No file selected."

    # Retrieve the updated list of files
    files_df = list_documents(collection_name)

    return feedback_text, files_df


def list_documents(collection_name: str) -> List[List[str]]:
    """
    Retrieve the list of document collections from the CSV file.

    This function fetches the current list of document names from the document list utility
    and formats them into a list of lists for display purposes.

    Returns:
        List[List[str]]: A list of lists containing the document names.
    """

    file_list = get_doc_list(collection_name)
    file_names = [[filename] for filename in file_list]
    logging.info("Document list retrieved.")
    return file_names


def _prepare_upload_folder() -> None:
    """
    Ensure the upload folder exists. Create it if it doesn't exist.

    This helper function checks for the existence of the upload directory specified by
    `UPLOAD_FOLDER`. If the directory does not exist, it creates it. Otherwise, it logs
    that the upload folder already exists.
    """
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
        logging.debug(f"Created upload folder at {UPLOAD_FOLDER}")
    else:
        logging.debug(f"Upload folder {UPLOAD_FOLDER} already exists.")


def list_collections() -> List[str]:
    return vector_store.list_collections()


def add_collection(collection_name: str):
    vector_store.add_collection(collection_name)
