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


logger = logging.getLogger(__name__)
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
    try:
        # Create upload folder if it does not exist
        _prepare_upload_folder()

        # Secure and copy the file to the upload folder
        file_name = os.path.basename(file_path)
        secure_file_name = secure_filename(file_name)
        temp_file_path = os.path.join(UPLOAD_FOLDER, secure_file_name)

        logger.debug(
            f"Processing document - collection: {collection_name}, file: {secure_file_name}"
        )

        shutil.copy(file_path, temp_file_path)
        logger.debug(f"Temporary file created: {temp_file_path}")

        file_hash = utils.compute_hash(temp_file_path)
        document_file_type = get_document_file_type(secure_file_name)

        logger.debug(
            f"Document analysis - file: {secure_file_name}, type: {document_file_type}, hash: {file_hash}"
        )

        if document_file_type is DocumentFileType.Document:
            # Check if the document is already up-to-date
            if _services["vector_store"].document_version_exists(
                collection_name=collection_name, file_hash=file_hash
            ):
                logger.info(
                    f"Document already up-to-date - collection: {collection_name}, file: {secure_file_name}"
                )
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
                logger.info(
                    f"Tabular document already up-to-date - collection: {collection_name}, file: {secure_file_name}"
                )
                return None

            _services["tabular_vector_store"].add_document(
                collection_name=collection_name,
                file_path=temp_file_path,
                file_hash=file_hash,
            )

        logger.info(
            f"Document added successfully - collection: {collection_name}, file: {secure_file_name}, type: {document_file_type}"
        )
        return secure_file_name

    except Exception as e:
        logger.error(
            f"Error adding document - collection: {collection_name}, file: {secure_file_name if 'secure_file_name' in locals() else file_path}: {e}",
            exc_info=True,
        )
        raise  # Re-raise the exception instead of returning None
    finally:
        # Ensure the temporary file is removed after processing
        if "temp_file_path" in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.debug(f"Temporary file removed: {temp_file_path}")


def add_documents(
    file_paths: List[str], collection_name: str = "pixie"
) -> List[List[str]]:
    """Add multiple documents to the system and retrieve the updated document list."""
    try:
        logger.debug(
            f"Adding multiple documents - collection: {collection_name}, count: {len(file_paths)}"
        )

        for file_path in file_paths:
            add_document(collection_name, file_path)

        df_files = list_documents(collection_name)
        logger.info(
            f"Multiple documents added successfully - collection: {collection_name}, total_count: {len(df_files)}"
        )
        return df_files
    except Exception as e:
        logger.error(
            f"Error adding multiple documents - collection: {collection_name}: {e}",
            exc_info=True,
        )
        raise


def remove_document(
    selected_file: str, collection_name: str = "pixie"
) -> List[List[str]]:
    try:
        if selected_file:
            document_file_type = get_document_file_type(selected_file)
            logger.debug(
                f"Removing document - collection: {collection_name}, file: {selected_file}, type: {document_file_type}"
            )

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
                    logger.info(
                        f"Document removed successfully - collection: {collection_name}, file: {selected_file}"
                    )
                else:
                    logger.warning(
                        f"Could not remove document - collection: {collection_name}, file: {selected_file}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to remove document - collection: {collection_name}, file: {selected_file}: {e}",
                    exc_info=True,
                )
        else:
            logger.warning("Attempted to remove document but no file was selected")

        # Retrieve the updated list of files
        files_df = list_documents(collection_name)
        return files_df
    except Exception as e:
        logger.error(
            f"Error in remove_document operation - collection: {collection_name}: {e}",
            exc_info=True,
        )
        raise


def list_documents(collection_name: str) -> List[List[str]]:
    """Retrieve the list of document collections."""
    try:
        logger.debug(f"Listing documents - collection: {collection_name}")

        def non_tabular(collection_name: str) -> List[str]:
            file_list = _services["vector_store"].get_documents(collection_name)
            return file_list

        def tabular(collection_name: str) -> List[str]:
            file_list = _services["tabular_vector_store"].get_documents(collection_name)
            return file_list

        file_list = non_tabular(collection_name) + tabular(collection_name)
        file_names = [[filename] for filename in file_list]
        logger.info(
            f"Document list retrieved - collection: {collection_name}, count: {len(file_names)}"
        )
        return file_names
    except Exception as e:
        logger.error(
            f"Error listing documents - collection: {collection_name}: {e}",
            exc_info=True,
        )
        return []


def _prepare_upload_folder() -> None:
    """
    Ensure the upload folder exists. Create it if it doesn't exist.

    This helper function checks for the existence of the upload directory specified by
    `UPLOAD_FOLDER`. If the directory does not exist, it creates it. Otherwise, it logs
    that the upload folder already exists.
    """
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            os.mkdir(UPLOAD_FOLDER)
            logger.debug(f"Upload folder created: {UPLOAD_FOLDER}")
        else:
            logger.debug(f"Upload folder already exists: {UPLOAD_FOLDER}")
    except Exception as e:
        logger.error(
            f"Error preparing upload folder {UPLOAD_FOLDER}: {e}", exc_info=True
        )
        raise


def list_collections() -> List[str]:
    try:
        logger.debug("Retrieving collections from both vector stores")
        collections = _services["vector_store"].get_collections()
        tabular_collections = _services["tabular_vector_store"].get_collections()
        logger.debug(f"RAG collections: {collections}")
        logger.debug(f"Tabular collections: {tabular_collections}")
        # assert set(collections) == set(tabular_collections)
        combined_collections = list(set(collections + tabular_collections))
        logger.info(f"Collections retrieved - total_count: {len(combined_collections)}")
        return combined_collections
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        return []


def add_collection(collection_name: str) -> None:
    """Add a collection to both vector stores."""
    try:
        logger.debug(f"Adding collection to both stores: {collection_name}")
        # NOTE: make this an atomic transaction in the future
        # because collections in both stores need to be in sync
        _services["vector_store"].add_collection(collection_name)
        _services["tabular_vector_store"].add_collection(collection_name)
        logger.info(f"Collection added to both stores successfully: {collection_name}")
    except Exception as e:
        logger.error(f"Failed to add collection {collection_name}: {e}", exc_info=True)
        raise
