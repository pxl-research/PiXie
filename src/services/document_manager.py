import os
import shutil
import logging
from typing import Optional, List

from werkzeug.utils import secure_filename

from services import utils

from services.document_loaders.document_loader_manager import (
    DocumentFileType,
    get_document_file_type,
)

# Import shared services for document management
from services.init_services import get_services

# Shared services for document management
_services = get_services()


UPLOAD_FOLDER = "./uploads"


def add_document(collection_name: str, file_path: str) -> Optional[str]:
    """
    Handle the process of uploading, securing the file name, and adding a document to the vector store.

    This function secures the filename, copies the file to the upload folder, computes its hash,
    checks if the document is up-to-date, and if not, processes the document and adds it to the
    appropriate vector store (RAG or tabular).

    Parameters:
        collection_name (str): The name of the collection to add the document to.
        file_path (str): The path of the file to handle.

    Returns:
        Optional[str]: The secure file name if added or updated, otherwise None.
        
    Raises:
        Exception: If document processing fails.
    """

    # Create upload folder if it does not exist
    _prepare_upload_folder()

    # Secure and copy the file to the upload folder
    file_name = os.path.basename(file_path)
    secure_file_name = secure_filename(file_name)
    temp_file_path = os.path.join(UPLOAD_FOLDER, secure_file_name)
    shutil.copy(file_path, temp_file_path)
    logging.info(f"Temporary file {temp_file_path} has been saved.")

    try:
        file_hash = utils.compute_hash(temp_file_path)
        document_file_type = get_document_file_type(secure_file_name)

        if document_file_type is DocumentFileType.Document:
            # Check if the document is already up-to-date
            if _services["vector_store"].document_version_exists(
                collection_name=collection_name, file_hash=file_hash
            ):
                logging.info(f"File {secure_file_name} is already up-to-date.")
                return None

            _services["vector_store"].add_document(
                collection_name=collection_name,
                file_path=temp_file_path,
                file_hash=file_hash,
            )

        elif document_file_type is DocumentFileType.TabularDocument:
            # Check if the document is already up-to-date
            if _services["tabular_vector_store"].document_version_exists(
                file_hash=file_hash, collection_name=collection_name
            ):
                logging.info(f"File {secure_file_name} is already up-to-date.")
                return None

            _services["tabular_vector_store"].add_document(
                collection_name=collection_name,
                file_path=temp_file_path,
                file_hash=file_hash,
            )

        logging.info(f"Document {secure_file_name} has been uploaded to remote store.")
        logging.info(f"Document {secure_file_name} has been added to the vector store.")
        return secure_file_name

    except Exception as e:
        logging.error(f"Error adding document {secure_file_name}: {str(e)}")
        raise  # Re-raise the exception instead of returning None
    finally:
        # Ensure the temporary file is removed after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logging.debug(f"Temporary file {temp_file_path} has been removed.")


def add_documents(
    file_paths: List[str], collection_name: str = "pixie"
) -> List[List[str]]:
    """Add multiple documents to the system and retrieve the updated document list."""

    for file_path in file_paths:
        add_document(collection_name, file_path)
    df_files = list_documents(collection_name)
    return df_files


def remove_document(
    selected_file: str, collection_name: str = "pixie"
) -> List[List[str]]:
    if selected_file:
        document_file_type = get_document_file_type(selected_file)
        logging.info(f"Removing document: {selected_file}")
        try:
            if document_file_type is DocumentFileType.Document:
                success = _services["vector_store"].delete_document(
                    collection_name, selected_file
                )
            elif document_file_type is DocumentFileType.TabularDocument:
                success = _services["tabular_vector_store"].delete_document(
                    collection_name, selected_file
                )
            else:
                raise Exception("No valid file extension used.")

            # Note: blob_service.delete_blob(selected_file) removed as it's not defined

            if success:
                logging.info(f"File '{selected_file}' has been successfully removed.")
            else:
                logging.info(f"Could not remove file '{selected_file}'.")
        except Exception as e:
            logging.error(f"Failed to remove file '{selected_file}': {e}")
    else:
        logging.info("Tried to remove document but no file was selected.")

    # Retrieve the updated list of files
    files_df = list_documents(collection_name)
    return files_df


def list_documents(collection_name: str) -> List[List[str]]:
    """Retrieve the list of document collections."""

    def non_tabular(collection_name: str) -> List[str]:
        file_list = _services["vector_store"].get_documents(collection_name)
        return file_list

    def tabular(collection_name: str) -> List[str]:
        file_list = _services["tabular_vector_store"].get_documents(collection_name)
        return file_list

    file_list = non_tabular(collection_name) + tabular(collection_name)
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
    collections = _services["vector_store"].get_collections()
    tabular_collections = _services["tabular_vector_store"].get_collections()
    logging.info(f"Collections: {collections}")
    logging.info(f"Tabular collections: {tabular_collections}")
    # assert set(collections) == set(tabular_collections)
    return list(set(collections + tabular_collections))


def add_collection(collection_name: str) -> None:
    """Add a collection to both vector stores."""
    try:
        # NOTE: make this an atomic transaction in the future
        # because collections in both stores need to be in sync
        _services["vector_store"].add_collection(collection_name)
        _services["tabular_vector_store"].add_collection(collection_name)
        logging.info(f"Collection '{collection_name}' added to both stores.")
    except Exception as e:
        logging.error(f"Failed to add collection '{collection_name}': {str(e)}")
        raise
