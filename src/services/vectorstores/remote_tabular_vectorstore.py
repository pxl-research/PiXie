import logging
from typing import Optional, List

import os
import pandas as pd
import requests
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
        Uploads a document file to the remote tabular vector store via the /collections/{collection_name}/documents endpoint.
        Args:
            collection_name (str): The name of the collection to upload to.
            file_path (str): The path to the file to upload.
            file_hash (str): The hash of the file.
        """
        try:
            file_name = Path(file_path).name
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                data = {"file_hash": file_hash}
                response = requests.post(
                    f"{self.url}/collections/{collection_name}/documents",
                    headers=self._get_file_headers(),
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
            response = self._delete(
                f"collections/{collection_name}/documents",
                {"file_name": file_name}
            )
            if response.status_code != 200:
                return False
            data = response.json()
            if data["success"]:
                logging.info(f"Document {file_name} deleted from {collection_name}.")
            return data["success"]
        except Exception as e:
            logging.error(f"Failed to delete document {file_name}: {str(e)}")
            return False

    def get_documents(self, collection_name: str) -> List[str]:
        """Retrieves a list of document file names in a collection."""
        response = self._get(f"collections/{collection_name}/documents")
        data = self._handle_response(response, error_message="Failed to list documents")
        return data.get("items", [])

    def document_version_exists(self, file_hash: str, collection_name: str) -> bool:
        """Check if a document version (hash) is up-to-date in the collection."""
        response = self._get(
            f"collections/{collection_name}/documents/version-exists",
            {"file_hash": file_hash},
        )
        data = self._handle_response(response, error_message="Failed to check document status")
        return data.get("success", False)

    def get_collections(self) -> List[str]:
        """Lists all collections in the tabular pgvector vector store."""
        response = self._get("collections")
        data = self._handle_response(response, error_message="Failed to list collections")
        return data.get("items", [])

    def add_collection(self, collection_name: str) -> None:
        """Adds a collection to the tabular pgvector vector store."""
        try:
            # Send collection_name as query parameter instead of JSON body
            response = self._post("collections", data=None, params={"collection_name": collection_name})
            data = self._handle_response(
                response, 
                f"Collection {collection_name} added successfully.",
                "Failed to add collection"
            )
            if not data.get("success"):
                logging.info(f"Collection {collection_name} already exists.")
        except Exception as e:
            logging.error(f"Failed to add collection {collection_name}: {str(e)}")
            raise

    def delete_collection(self, collection_name: str) -> None:
        """
        Deletes a collection and its associated relations from the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        try:
            response = self._delete("collections", {"collection_name": collection_name})
            data = self._handle_response(
                response,
                f"Collection {collection_name} deleted successfully.",
                "Failed to delete collection"
            )
            if not data.get("success"):
                logging.info(f"Collection {collection_name} does not exist.")
        except Exception as e:
            logging.error(f"Failed to delete collection {collection_name}: {str(e)}")
            raise

    def get_summaries(self, collection_name: str) -> List[str]:
        """Retrieves file descriptions for a collection."""
        response = self._get(f"collections/{collection_name}/summaries")
        data = self._handle_response(response, error_message="Failed to get summaries")
        return data.get("items", [])

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
            max_file_count (int, optional): Maximum number of files to consider
                based on schema matching. Default is 3.

        Returns:
            pd.DataFrame: DataFrame containing the attributes of the top matching rows.
        """
        try:
            response = requests.get(
                f"{self.url}/collections/{collection_name}/search",
                headers={"x-api-key": os.getenv("RAG_API_KEY")},
                params={
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
            if "data" not in data:
                raise Exception("Invalid response format: 'data' key missing.")
            return pd.DataFrame(data["data"])
        except Exception as e:
            logging.error(f"Failed to retrieve top rows: {str(e)}")
            raise

    # Helper methods
    def _handle_response(self, response, success_message: str = None, error_message: str = "Request failed"):
        """Common response handling logic."""
        if response.status_code != 200:
            raise Exception(f"{error_message}: {response.text}")
        
        data = response.json()
        if success_message and data.get("success"):
            logging.info(success_message)
        
        return data

    def _get(self, call: str, data: Optional[dict] = None):
        return requests.get(
            f"{self.url}/{call}",
            headers=self._get_headers(),
            params=data,
        )

    def _post(self, call: str, data: dict = None, params: dict = None):
        """Updated _post method to support both JSON body and query params."""
        return requests.post(
            f"{self.url}/{call}",
            headers=self._get_headers(),
            json=data if data is not None else None,
            params=params,
        )

    def _delete(self, call: str, data: Optional[dict] = None):
        return requests.delete(
            f"{self.url}/{call}",
            headers=self._get_headers(),
            params=data,
        )

    def _get_headers(self) -> dict:
        """Returns common headers for API requests."""
        return {
            "Content-Type": "application/json",
            "x-api-key": os.getenv("RAG_API_KEY"),
        }

    def _get_file_headers(self) -> dict:
        """Returns headers for file upload requests (no Content-Type)."""
        return {
            "x-api-key": os.getenv("RAG_API_KEY"),
        }
