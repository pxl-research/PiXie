from services.abstractclasses.vectorstore import VectorStore
from typing import List, Optional
import requests
import os
import logging
from pathlib import Path


class RemoteRagVectorStore(VectorStore):
    def __init__(self, url: str):
        self.url = url

    def add_document(
        self, collection_name: str, file_path: str, file_hash: str
    ) -> None:
        """
        Uploads a document file to the remote vector store.
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
        Deletes a document from the remote vector store.

        Args:
            collection_name (str): The name of the collection.
            file_name (str): The name of the document to delete.

        Returns:
            bool: True if the document was successfully deleted, False otherwise.
        """
        try:
            response = self._delete(
                f"collections/{collection_name}/documents", {"document_name": file_name}
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
        """Retrieves the list of documents in a collection."""
        response = self._get(f"collections/{collection_name}/documents")
        data = self._handle_response(
            response, error_message="Failed to get document list"
        )
        return data.get("items", [])

    def get_summaries(self, collection_name: str) -> List[str]:
        """Retrieves file summaries/descriptions for a collection."""
        response = self._get(f"collections/{collection_name}/summary")
        data = self._handle_response(response, error_message="Failed to get summaries")
        return data.get("items", [])

    def document_exists(self, collection_name: str, file_name: str) -> bool:
        """Checks if a document exists in the collection."""
        response = self._get(
            f"collections/{collection_name}/documents/exists",
            {"file_name": file_name},
        )
        data = self._handle_response(
            response, error_message="Failed to check document status"
        )
        return data.get("success", False)

    def document_version_exists(self, collection_name: str, file_hash: str) -> bool:
        """Checks if a document version (hash) exists in the collection."""
        response = self._get(
            f"collections/{collection_name}/documents/version-exists",
            {"file_hash": file_hash},
        )
        data = self._handle_response(
            response, error_message="Failed to check document status"
        )
        return data.get("success", False)

    def add_collection(self, collection_name: str) -> None:
        """Adds a collection to the remote vector store."""
        try:
            # Send collection_name as query parameter instead of JSON body
            response = self._post("collections", data=None, params={"collection_name": collection_name})
            self._handle_response(
                response,
                f"Collection {collection_name} added successfully.",
                "Failed to add collection",
            )
        except Exception as e:
            logging.error(f"Failed to add collection {collection_name}: {str(e)}")
            raise

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the remote vector store."""
        try:
            # This one is already correct - uses params
            response = self._delete("collections", {"collection_name": collection_name})
            self._handle_response(
                response,
                f"Collection {collection_name} deleted successfully.",
                "Failed to delete collection",
            )
        except Exception as e:
            logging.error(f"Failed to delete collection {collection_name}: {str(e)}")
            raise

    def get_collections(self) -> List[str]:
        """Lists all collections in the remote vector store."""
        response = self._get("collections")
        data = self._handle_response(
            response, error_message="Failed to list collections"
        )
        if "items" not in data:
            raise Exception("Invalid response format: 'items' key missing.")
        return data["items"]

    # Helper methods remain the same
    def _handle_response(
        self,
        response,
        success_message: str = None,
        error_message: str = "Request failed",
    ):
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
