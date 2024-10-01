import os
import shutil
import logging
from werkzeug.utils import secure_filename
from services import utils, blob_service
from typing import List, Tuple
from app import document_loader, splitter, vector_store, reranker
from page_numbering import text_chunks_to_page_numbers

UPLOAD_FOLDER = "./uploads"
DOC_LIST_PATH = "src/assets/helper/doc_list.csv"


def retrieve_and_rerank_chunks(message, top_k=15, final_k=5):
    """Retrieve chunks and optionally rerank them based on the input message."""
    top_chunks = vector_store.retrieve_top_chunks(message, top_k)

    if reranker is not None:
        final_chunks = reranker.rerank(message, top_chunks, final_k)
        logging.info(f"Chunks have been reranked for the message: {message}")
    else:
        final_chunks = top_chunks[:final_k]
        logging.info(
            f"No reranker available. Returning top {final_k} chunks for the message: {message}"
        )

    return final_chunks


def add_document(file_path: str) -> str:
    """
    Handle the process of uploading, securing the file name, loading, splitting,
    and adding a document to the vector store.

    Parameters:
    - file_path: str
        The path of the file to handle.

    Returns:
    - str: The secure file name if added or updated, otherwise None.
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
        if utils.is_doc_up_to_date_in_list(file_hash, DOC_LIST_PATH):
            logging.info(f"File {secure_file_name} is already up-to-date.")
            return None

        delete = utils.is_doc_in_list(secure_file_name, DOC_LIST_PATH)

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

        vector_store.add_document(secure_file_name, chunks)

        # Update the document list
        utils.add_to_doc_list(DOC_LIST_PATH, secure_file_name, file_hash, delete)

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


def remove_document(file_name: str) -> None:
    """
    Remove a document from the vector store, the collection list, and Azure Blob Storage.

    Parameters:
    - file_name: str
        The name of the file to remove.
    """
    try:
        vector_store.delete_document(file_name)
        utils.remove_from_doc_list(DOC_LIST_PATH, file_name)
        blob_service.delete_blob(file_name)

        logging.info(
            f"Removed document {file_name} from the vector store, document list, and Azure Blob Storage."
        )
    except Exception as e:
        logging.error(f"Failed to remove document {file_name}: {e}")


def list_documents() -> List[str]:
    """
    Retrieve the list of document collections from the CSV file.

    Returns:
    - List[str]: A list of file names in the document collection.
    """
    doc_list = utils.get_doc_list(DOC_LIST_PATH)
    print([[file_name] for file_name in doc_list["file_name"]])
    logging.info("Document list retrieved.")
    return [[file_name] for file_name in doc_list["file_name"]]


def _prepare_upload_folder() -> None:
    """
    Ensure the upload folder exists. Create it if it doesn't exist.
    """
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
        logging.debug(f"Created upload folder at {UPLOAD_FOLDER}")
    else:
        logging.debug(f"Upload folder {UPLOAD_FOLDER} already exists.")
