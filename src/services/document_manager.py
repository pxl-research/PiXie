import os
import shutil
import logging
import pandas as pd
from werkzeug.utils import secure_filename
from typing import Optional

from services import utils

from services.document_loaders.document_loader_manager import (
    DocumentFileType,
    get_document_file_type,
)

import numpy as np
from langdetect import detect, DetectorFactory
from collections import Counter

# Import shared services for document management
from services.init_services import get_services

# Shared services for document management
_services = get_services()
tabular_vector_store = _services["tabular_vector_store"]

# Fix randomness in langdetect
DetectorFactory.seed = 42

UPLOAD_FOLDER = "./uploads"


def detect_language_from_dataframe_samples(
    df: pd.DataFrame, n: int = 10
) -> Optional[str]:
    """
    Sample up to n rows evenly spaced across the DataFrame and detect language.

    Parameters:
        df (pd.DataFrame): The DataFrame to sample.
        n (int): Maximum number of rows to sample (default is 10).

    Returns:
        str: detected language
    """
    if n < 0:
        n = 0
    elif n > len(df):
        n = len(df)

    indices = list(
        map(int, np.linspace(0, len(df) - 1, n))
    )  # evenly spaced row indices
    sampled_rows = df.iloc[indices]  # sample n rows

    # Flatten text values from sampled rows for language detection
    text_samples = []
    for row in sampled_rows.itertuples(index=False):
        for value in row:
            if isinstance(value, str) and len(value.strip()) > 0:
                text_samples.append(value.strip())
    # print(text_samples)

    # Detect language from sampled text
    default_language = os.getenv("DEFAULT_LANGUAGE")
    detected_languages = []
    for text in text_samples[: min(len(text_samples), 10)]:  # Limit to 10 texts
        try:
            detected_languages.append(detect(text))
        except Exception:
            continue  # Skip text that cannot be detected

    if len(detected_languages) <= 0:
        return default_language

    most_common_lang = Counter(detected_languages).most_common(1)
    return most_common_lang[0][0] if most_common_lang else default_language


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
            if _services["vector_store"].is_doc_up_to_date_in_list(
                file_hash=file_hash, collection_name=collection_name
            ):
                logging.info(f"File {secure_file_name} is already up-to-date.")
                return None

            _services["vector_store"].add_document(
                collection_name=collection_name,
                file_path=temp_file_path,
                file_hash=file_hash,
            )

        elif document_file_type is DocumentFileType.TabularDocument:
            logging.info(
                f"Processing tabular document: {secure_file_name} of type {document_file_type}"
            )
        #     # Check if the document is already up-to-date: new hash is the same as stored
        #     # No further actions needed
        #     loaded_data = document
        #     if tabular_vector_store.is_doc_up_to_date_in_list(
        #         file_hash, collection_name
        #     ):
        #         logging.info(f"File {secure_file_name} is already up-to-date.")
        #         return None

        #     # If document is already stored, but different hash (thus different content)
        #     # Delete it first and insert it again later
        #     # We do this for every sheet
        #     prohibited_chars = "\\/?*[]"
        #     if isinstance(loaded_data, pd.DataFrame):
        #         # will be unique, because in Excel a sheetname cannot be one of those chars
        #         dict_data = {prohibited_chars: loaded_data}
        #     elif isinstance(loaded_data, dict):
        #         dict_data = loaded_data
        #     else:
        #         return None

        #     for sheet_name, df in dict_data.items():
        #         if sheet_name == prohibited_chars and len(dict_data) == 1:
        #             secure_file_name_sheet = secure_file_name
        #         else:
        #             secure_file_name_sheet = f"{secure_file_name}#{sheet_name}"

        #         # Is not necessary, since we already do this
        #         # in add_tabular_document()
        #         """
        #         will_delete = tabular_vector_store.is_doc_in_list(
        #             secure_file_name_sheet, collection_name
        #         )
        #         if will_delete:
        #             tabular_vector_store.delete_tabular_document(
        #                 collection_name, secure_file_name_sheet
        #             )
        #         """

        #         file_description = _services["tabular_summarizer"].generate(df=df)
        #         logging.info(f"File description: {file_description}")
        #         if file_description is None:
        #             file_description = ""

        #         # Infer language from DataFrame df
        #         language = detect_language_from_dataframe_samples(df, n=10)
        #         if language is None:
        #             language = os.getenv("DEFAULT_LANGUAGE")

        #         # Use map on each column instead of deprecated applymap
        #         for col in df.columns:
        #             df[col] = df[col].map(
        #                 lambda x: (
        #                     x.isoformat()
        #                     if isinstance(
        #                         x, (pd.Timestamp, datetime.datetime, datetime.date)
        #                     )
        #                     else x
        #                 )
        #             )

        #         tabular_vector_store.add_document(
        #             collection_name=collection_name,
        #             file_name=secure_file_name_sheet,
        #             file_hash=file_hash,
        #             file_description=file_description,
        #             language=language,
        #             df=df,
        #         )
        # else:
        #     return None

        # # Upload the file to Azure Blob Storage
        # blob_service.upload_blob(temp_file_path, secure_file_name)
        logging.info(
            f"Document {secure_file_name} has been uploaded to Azure Blob Storage."
        )
        logging.info(
            f"Document {secure_file_name} has been added to the tabular vector store."
        )

        return secure_file_name

    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        # Ensure the temporary file is removed after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logging.debug(f"Temporary file {temp_file_path} has been removed.")


def add_documents(
    file_paths: list[str], collection_name: str = "pixie"
) -> list[list[str]]:
    """
    Add multiple documents to the system and retrieve the updated document list.

    This function iterates over a list of file paths, adding each document to the document store
    by invoking the `add_document` function. After all documents are added, it retrieves the updated
    list of document collections by calling `list_documents`.

    Parameters:
        file_paths (list[str]): A list of file paths representing the documents to be added.

    Returns:
        list[list[str]]: An updated list of document collections, where each inner list contains
        information about a single document.
    """

    for file_path in file_paths:
        add_document(collection_name, file_path)
    df_files = list_documents(collection_name)
    return df_files


def remove_document(
    selected_file: str, collection_name: str = "pixie"
) -> list[list[str]]:
    if selected_file:
        document_file_type = get_document_file_type(selected_file)
        logging.info(f"Removing document: {selected_file}")
        try:
            if document_file_type is DocumentFileType.Document:
                success_deletion_from_vector_store = _services[
                    "vector_store"
                ].delete_document(collection_name, selected_file)
                success_deletion_from_doc_list = _services[
                    "vector_store"
                ].remove_from_doc_list(selected_file, collection_name)
                success = (
                    success_deletion_from_vector_store
                    and success_deletion_from_doc_list
                )
            elif document_file_type is DocumentFileType.TabularDocument:
                success = tabular_vector_store.delete_tabular_document(
                    collection_name, selected_file
                )
            else:
                raise Exception("No valid file extension used.")
            blob_service.delete_blob(selected_file)

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


def list_documents(collection_name: str) -> list[list[str]]:
    """
    Retrieve the list of document collections.

    This function fetches the current list of document names from the document list utility
    and formats them into a list of lists for display purposes.

    Returns:
        list[list[str]]: A list of lists containing the document names.
    """

    def non_tabular(collection_name: str) -> list[str]:
        file_list = _services["vector_store"].get_doc_list(collection_name)
        return file_list

    def tabular(collection_name: str) -> list[str]:
        file_list = tabular_vector_store.list_documents(collection_name)
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


def list_collections() -> list[str]:
    collections = _services["vector_store"].list_collections()
    tabular_collections = tabular_vector_store.list_collections()
    print("Collections:")
    print(collections)
    print("Tabular collections:")
    print(tabular_collections)
    # assert set(collections) == set(tabular_collections)
    return list(set(collections + tabular_collections))


def add_collection(collection_name: str) -> None:
    # NOTE: make this an atomic transaction in the future
    # because collections in both stores need to be in sync
    _services["vector_store"].add_collection(collection_name)
    tabular_vector_store.add_collection(collection_name)
