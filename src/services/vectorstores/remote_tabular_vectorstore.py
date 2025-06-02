import logging
from typing import Optional, List
import pandas as pd
import requests
import os

from langchain_core.documents import Document
from pathlib import Path


class RemoteTabularVectorStore:
    """
    Postgres pgvector implementation of a TabularVectorStore working on tabular data.
    """

    def __init__(self, url: str):
        self.url = url

    def add_document(
        self, collection_name: str, file_path: str, file_hash: str
    ) -> None:
        """
        Uploads a document file to the remote tabular vector store via the /upload_raw endpoint.
        Args:
            collection_name (str): The name of the collection to upload to.
            file_path (str): The path to the file to upload.
            file_hash (str): The hash of the file.
        """
        try:
            file_name = Path(file_path).name
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                data = {
                    "collection_name": collection_name,
                    "file_hash": file_hash,
                }
                response = requests.post(
                    f"{self.url}/upload_raw",
                    headers={"x-api-key": os.getenv("RAG_API_KEY")},
                    files=files,
                    data=data,
                )
            if response.status_code != 200:
                raise Exception(f"Failed to upload document: {response.text}")
            logging.info(f"Document '{file_name}' uploaded to '{collection_name}'.")
        except Exception as e:
            logging.error(f"Failed to upload document {file_path}: {str(e)}")
            raise

    def delete_document(self, collection_name: str, file_name: str) -> bool:
        """
        Deletes one or more tabular documents from the tabular pgvector vector store
        based on the collection and file name or file name pattern.

        Args:
            collection_name (str): The name of the collection the document(s) belong to.
            file_name (str): The name or pattern of the files to delete.

        Returns:
            bool: True if at least one document was deleted, False otherwise.
        """
        try:
            response = self._get(
                "delete_document",
                {
                    "collection_name": collection_name,
                    "file_name": file_name,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to delete document: {response.text}")
            data = response.json()
            if data["success"]:
                logging.info(f"Document {file_name} deleted from {collection_name}.")
                return True
        except Exception as e:
            logging.error(f"Failed to delete document {file_name}: {str(e)}")
        return False

    def retrieve_top_rows(
        self,
        collection_name: str,
        question: str,
        top_k: int = 30,
        k_rrf: int = 60,
        max_file_count: int = 3,
        try_iteration_max_count=3,
        is_recommendation_system: bool = False,
    ) -> pd.DataFrame:
        """
        Retrieve the top rows relevant to a question from a specified collection.

        Args:
            collection_name (str): Name of the collection to search within.
            question (str): The query or question for which relevant rows are retrieved.
            top_k (int, optional): Number of top rows to return. Default is 10.
            k_rrf (int, optional): Reciprocal rank fusion parameter. Default is 60.
            weight_row_vs_file_based (float, optional): Weight to balance
                row-level vs. file-level relevance scores. Default is 0.8.
            max_file_count (int, optional): Maximum number of files to consider
                based on schema matching. Default is 3.

        Returns:
            pd.DataFrame: DataFrame containing the attributes of the top matching rows.
        """
        try:
            response = self._get(
                "retrieve_top_rows",
                {
                    "collection_name": collection_name,
                    "question": question,
                    "top_k": top_k,
                    "k_rrf": k_rrf,
                    "max_file_count": max_file_count,
                    "try_iteration_max_count": try_iteration_max_count,
                    "is_recommendation_system": is_recommendation_system,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to retrieve top rows: {response.text}")
            data = response.json()
            if "rows" not in data:
                raise Exception("Invalid response format: 'rows' key missing.")
            return pd.DataFrame(pd.DataFrame(data["rows"]))
        except Exception as e:
            logging.error(f"Failed to retrieve top rows: {str(e)}")
            raise

    def list_documents(self, collection_name: str) -> List[str]:
        """
        Retrieves a list of document file names associated with a specific collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            list[str]: A list of document file names in the collection.
        """
        try:
            response = self._get(
                "list_documents",
                {
                    "collection_name": collection_name,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to list documents: {response.text}")
            data = response.json()
            if "items" not in data:
                raise Exception("Invalid response format: 'documents' key missing.")
            return data["items"]
        except Exception as e:
            logging.error(f"Failed to list documents: {str(e)}")
            raise

    def is_doc_up_to_date_in_list(self, file_hash: str, collection_name: str) -> bool:
        """
        Check if a tabular document with a given hash is up-to-date
        in the tabular document list for a specific collection.

        Args:
            file_hash (str): The hash of the tabular document to check.
            collection (str): The collection the tabular document belongs to.

        Returns:
            bool: True if the document is up-to-date, False otherwise.
        """
        try:
            response = self._get(
                "is_doc_up_to_date",
                {
                    "file_hash": file_hash,
                    "collection_name": collection_name,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to check document status: {response.text}")
            data = response.json()
            if data["success"]:
                logging.info(
                    f"Document with hash {file_hash} is up-to-date in collection {collection_name}."
                )
                return True
            else:
                logging.info(
                    f"Document with hash {file_hash} is NOT up-to-date in collection {collection_name}."
                )
                return False
        except Exception as e:
            logging.error(f"Failed to check document status: {str(e)}")
            return False

    def list_collections(self) -> list[str]:
        """
        Lists all collections in the tabular pgvector vector store.

        Returns:
            list[str]: A list of collection names.
        """
        try:
            response = self._get("list_collections")
            if response.status_code != 200:
                raise Exception(f"Failed to list collections: {response.text}")
            data = response.json()
            if "items" not in data:
                raise Exception("Invalid response format: 'collections' key missing.")
            return data["items"]
        except Exception as e:
            logging.error(f"Failed to list collections: {str(e)}")
            raise

    def add_collection(self, collection_name: str) -> None:
        """
        Adds a collection to the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to add.
        """
        try:
            response = self._get(
                "add_collection",
                {
                    "collection_name": collection_name,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to add collection: {response.text}")
            data = response.json()
            if data["success"]:
                logging.info(f"Collection {collection_name} added successfully.")
            else:
                logging.info(f"Collection {collection_name} already exists.")
        except Exception as e:
            logging.error(f"Failed to add collection {collection_name}: {str(e)}")
            raise

    def remove_collection(self, collection_name: str) -> None:
        """
        Deletes a collection and its associated relations from the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        try:
            response = self._get(
                "remove_collection",
                {
                    "collection_name": collection_name,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to remove collection: {response.text}")
            data = response.json()
            if data["success"]:
                logging.info(f"Collection {collection_name} removed successfully.")
            else:
                logging.info(f"Collection {collection_name} does not exist.")
        except Exception as e:
            logging.error(f"Failed to remove collection {collection_name}: {str(e)}")
            raise

    def get_summaries_by_collection(self, collection_name: str) -> list[str]:
        """
        Retrieves a list of file_descriptions associated with a specific collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            list[str]: A list of file descriptions in the collection.
        """
        try:
            response = self._get(
                "get_summaries",
                {
                    "collection_name": collection_name,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to get summaries: {response.text}")
            data = response.json()
            if "items" not in data:
                raise Exception("Invalid response format: 'summaries' key missing.")
            return data["items"]
        except Exception as e:
            logging.error(f"Failed to get summaries: {str(e)}")
            raise

    def retrieve_top_chunks(
        self, collection_name: str, question: str, k: int
    ) -> List[Document]:
        """
        Retrieves the top K most similar document chunks to the given question.

        Args:
            question (str): The query to search for.
            k (int): The number of top results to return.

        Returns:
            List[Document]: A list of the top K similar documents.
        """
        logging.info("Calling obsolete function to retrieve top chunks.")
        return []

    def _get(self, call: str, data: Optional[dict] = None):
        return requests.get(
            f"{self.url}/{call}",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("RAG_API_KEY"),
            },
            params=data,
        )

    def _post(self, call: str, data: dict):
        return requests.post(
            f"{self.url}/{call}",
            headers={
                "Content-Type": "application/json",
                "x-api-key": os.getenv("RAG_API_KEY"),
            },
            json=data,
        )
