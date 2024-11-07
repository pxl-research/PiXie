from services.database.database import get_db_connection
import logging
from typing import List, Optional, Tuple


def is_doc_up_to_date_in_list(file_hash: str, collection: str) -> bool:
    """
    Check if a document with a given hash is up-to-date in the document list for a specific collection.

    Parameters:
        file_hash (str): The hash of the document to check.
        collection (str): The collection the document belongs to.

    Returns:
        bool: True if the document is up-to-date, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT file_hash FROM documents WHERE file_hash = %s AND collection = %s",
                (file_hash, collection),
            )
            result = cursor.fetchone()
            return result is not None
    finally:
        conn.close()


def is_doc_in_list(file_name: str, collection: str) -> bool:
    """
    Check if a document with a given name exists in the document list for a specific collection.

    Parameters:
        file_name (str): The name of the document to check.
        collection (str): The collection the document belongs to.

    Returns:
        bool: True if the document exists in the list, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT file_name FROM documents WHERE file_name = %s AND collection = %s",
                (file_name, collection),
            )
            result = cursor.fetchone()
            return result is not None
    finally:
        conn.close()


def add_to_doc_list(
    file_name: str,
    file_hash: str,
    collection: str,
    summary: Optional[str] = None,
    delete: bool = False,
) -> None:
    """
    Add a document to the document list for a specific collection or update the last updated timestamp.

    Parameters:
        file_name (str): The name of the document to add or update.
        file_hash (str): The hash of the document.
        collection (str): The collection the document belongs to.
        summary (str, optional): The summary of the document. Defaults to None.
        delete (bool, optional): If True, delete the old document entry before adding the new one. Defaults to False.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if delete:
                cursor.execute(
                    "DELETE FROM documents WHERE file_name = %s AND collection = %s",
                    (file_name, collection),
                )
            cursor.execute(
                """
                INSERT INTO documents (file_name, file_hash, last_updated, collection, summary)
                VALUES (%s, %s, NOW(), %s, %s)
                ON CONFLICT (file_name, collection) DO UPDATE
                SET file_hash = EXCLUDED.file_hash,
                    last_updated = EXCLUDED.last_updated,
                    summary = EXCLUDED.summary
                """,
                (file_name, file_hash, collection, summary),
            )
        conn.commit()
        logging.info(
            f"Document '{file_name}' added/updated in collection '{collection}'."
        )
    finally:
        conn.close()


def remove_from_doc_list(file_name: str, collection: str) -> bool:
    """
    Remove a document from the document list in a specific collection.

    Parameters:
        file_name (str): The name of the document to remove.
        collection (str): The collection the document belongs to.

    Returns:
        bool: True if the document was successfully removed, False otherwise.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM documents WHERE file_name = %s AND collection = %s",
                (file_name, collection),
            )
            conn.commit()
            logging.info(
                f"Document '{file_name}' removed from collection '{collection}'."
            )
            return True
    except Exception as e:
        logging.error(
            f"Error removing document '{file_name}' from collection '{collection}': {e}"
        )
        return False
    finally:
        conn.close()


def get_doc_list(collection: str) -> List[str]:
    """
    Retrieve the list of documents from a specific collection.

    Parameters:
        collection (str): The collection to retrieve the documents from.

    Returns:
        List[str]: A list of file names in the specified collection.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT file_name FROM documents WHERE collection = %s", (collection,)
            )
            filenames = cursor.fetchall()
            logging.info(f"Document list for collection '{collection}' retrieved.")
            return [[file_name[0]] for file_name in filenames]
    finally:
        conn.close()


def get_summaries_by_collection(collection_name: str) -> List[str]:
    """
    Retrieve summaries for a specific collection from the database.

    Args:
        collection_name (str): The name of the collection.

    Returns:
        List[str]: A list of summaries from the specified collection.
    """
    # Connect to your PostgreSQL database
    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            # Execute the query
            cursor.execute(
                "SELECT summary FROM documents WHERE collection = %s",
                (collection_name,),
            )

            # Fetch all results and extract summaries
            summaries = [row[0] for row in cursor.fetchall()]

            return summaries
    finally:
        # Close the connection
        conn.close()
