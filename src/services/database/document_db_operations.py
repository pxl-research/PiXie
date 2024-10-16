from services.database.database import get_db_connection
import logging
from typing import List


def is_doc_up_to_date_in_list(file_hash: str) -> bool:
    """
    Check if a document with a given hash is up-to-date in the document list.

    This function queries the 'documents' table in the PostgreSQL database to verify
    if a document with the specified hash already exists.

    Parameters:
        file_hash (str): The hash of the document to check.

    Returns:
        bool: True if the document is up-to-date, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT file_hash FROM documents WHERE file_hash = %s", (file_hash,)
            )
            result = cursor.fetchone()
            return result is not None
    finally:
        conn.close()


def is_doc_in_list(file_name: str) -> bool:
    """
    Check if a document with a given name exists in the document list.

    This function queries the 'documents' table in the PostgreSQL database to verify
    if a document with the specified name already exists.

    Parameters:
        file_name (str): The name of the document to check.

    Returns:
        bool: True if the document exists in the list, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT file_name FROM documents WHERE file_name = %s", (file_name,)
            )
            result = cursor.fetchone()
            return result is not None
    finally:
        conn.close()


def add_to_doc_list(file_name: str, file_hash: str, delete: bool = False) -> None:
    """
    Add a document to the document list or update the last updated timestamp.

    This function inserts a new document record into the 'documents' table in the PostgreSQL database.
    If the document already exists and `delete` is True, it first deletes the existing record before
    adding the new one. If the document exists and `delete` is False, it updates the existing record
    with the new hash and updates the timestamp.

    Parameters:
        file_name (str): The name of the document to add or update.
        file_hash (str): The hash of the document.
        delete (bool, optional): If True, delete the old document entry before adding the new one. Defaults to False.

    Returns:
        None
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if delete:
                cursor.execute(
                    "DELETE FROM documents WHERE file_name = %s", (file_name,)
                )
            cursor.execute(
                """
                INSERT INTO documents (file_name, file_hash, last_updated)
                VALUES (%s, %s, NOW())
                ON CONFLICT (file_name) DO UPDATE
                SET file_hash = EXCLUDED.file_hash,
                    last_updated = EXCLUDED.last_updated
                """,
                (file_name, file_hash),
            )
        conn.commit()
        logging.info(f"Document '{file_name}' added/updated in the document list.")
    finally:
        conn.close()


def remove_from_doc_list(file_name: str) -> bool:
    """
    Remove a document from the document list.

    This function deletes the specified document from the 'documents' table in the PostgreSQL database.

    Parameters:
        file_name (str): The name of the document to remove.

    Returns:
        bool: True if the document was successfully removed, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE file_name = %s", (file_name,))
            conn.commit()
            logging.info(f"Document '{file_name}' removed from the document list.")
            return True
    except Exception as e:
        logging.error(f"Error removing document '{file_name}': {e}")
        return False
    finally:
        conn.close()


def get_doc_list() -> List[str]:
    """
    Retrieve the list of documents from the database.

    This function queries the 'documents' table in the PostgreSQL database and retrieves
    all document names.

    Returns:
        List[str]: A list of file names in the document collection.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT file_name FROM documents")
            filenames = cursor.fetchall()
            logging.info("Document list retrieved.")
            return [[file_name[0]] for file_name in filenames]
    finally:
        conn.close()
