from services.abstractclasses.vectorstore import VectorStore
from typing import List, Optional
import requests
import os
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class RemoteRagVectorStore(VectorStore):
    def __init__(self, url: str):
        self.url = url
        logger.debug(f"Initialized RemoteRagVectorStore with URL: {url}")

    def add_document(
        self, collection_name: str, file_path: str, file_hash: str
    ) -> None:
        """
        Uploads a document file to the remote vector store.
        """
        try:
            file_name = Path(file_path).name
            logger.debug(
                f"Adding document - collection: {collection_name}, file: {file_name}, hash: {file_hash}"
            )

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
            logger.info(
                f"Document uploaded successfully - collection: {collection_name}, file: {file_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to upload document - collection: {collection_name}, file: {file_path}: {e}",
                exc_info=True,
            )
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
            logger.debug(
                f"Deleting document - collection: {collection_name}, file: {file_name}"
            )
            response = self._delete(
                f"collections/{collection_name}/documents", {"document_name": file_name}
            )
            if response.status_code != 200:
                logger.warning(
                    f"Delete request failed - collection: {collection_name}, file: {file_name}, status: {response.status_code}"
                )
                return False
            data = response.json()
            if data["success"]:
                logger.info(
                    f"Document deleted successfully - collection: {collection_name}, file: {file_name}"
                )
            else:
                logger.warning(
                    f"Document deletion unsuccessful - collection: {collection_name}, file: {file_name}"
                )
            return data["success"]
        except Exception as e:
            logger.error(
                f"Failed to delete document - collection: {collection_name}, file: {file_name}: {e}",
                exc_info=True,
            )
            return False

    def get_documents(self, collection_name: str) -> List[str]:
        """Retrieves the list of documents in a collection."""
        try:
            logger.debug(f"Retrieving documents - collection: {collection_name}")
            response = self._get(f"collections/{collection_name}/documents")
            data = self._handle_response(
                response, error_message="Failed to get document list"
            )
            documents = data.get("items", [])
            logger.info(
                f"Retrieved documents - collection: {collection_name}, count: {len(documents)}"
            )
            return documents
        except Exception as e:
            logger.error(
                f"Failed to retrieve documents - collection: {collection_name}: {e}",
                exc_info=True,
            )
            return []

    def get_summaries(self, collection_name: str) -> List[str]:
        """Retrieves file summaries/descriptions for a collection."""
        try:
            logger.debug(f"Retrieving summaries - collection: {collection_name}")
            response = self._get(f"collections/{collection_name}/summary")
            data = self._handle_response(
                response, error_message="Failed to get summaries"
            )
            summaries = data.get("items", [])
            logger.info(
                f"Retrieved summaries - collection: {collection_name}, count: {len(summaries)}"
            )
            return summaries
        except Exception as e:
            logger.error(
                f"Failed to retrieve summaries - collection: {collection_name}: {e}",
                exc_info=True,
            )
            return []

    def document_exists(self, collection_name: str, file_name: str) -> bool:
        """Checks if a document exists in the collection."""
        try:
            logger.debug(
                f"Checking document existence - collection: {collection_name}, file: {file_name}"
            )
            response = self._get(
                f"collections/{collection_name}/documents/exists",
                {"file_name": file_name},
            )
            data = self._handle_response(
                response, error_message="Failed to check document status"
            )
            exists = data.get("success", False)
            logger.debug(
                f"Document existence check result - collection: {collection_name}, file: {file_name}, exists: {exists}"
            )
            return exists
        except Exception as e:
            logger.error(
                f"Failed to check document existence - collection: {collection_name}, file: {file_name}: {e}",
                exc_info=True,
            )
            return False

    def document_version_exists(self, collection_name: str, file_hash: str) -> bool:
        """Checks if a document version (hash) exists in the collection."""
        try:
            logger.debug(
                f"Checking document version - collection: {collection_name}, hash: {file_hash}"
            )
            response = self._get(
                f"collections/{collection_name}/documents/version-exists",
                {"file_hash": file_hash},
            )
            data = self._handle_response(
                response, error_message="Failed to check document status"
            )
            exists = data.get("success", False)
            logger.debug(
                f"Document version check result - collection: {collection_name}, exists: {exists}"
            )
            return exists
        except Exception as e:
            logger.error(
                f"Failed to check document version - collection: {collection_name}, hash: {file_hash}: {e}",
                exc_info=True,
            )
            return False

    def add_collection(self, collection_name: str) -> None:
        """Adds a collection to the remote vector store."""
        try:
            logger.debug(f"Adding collection: {collection_name}")
            # Send collection_name as query parameter instead of JSON body
            response = self._post(
                "collections", data=None, params={"collection_name": collection_name}
            )
            self._handle_response(
                response,
                f"Collection {collection_name} added successfully.",
                "Failed to add collection",
            )
            logger.info(f"Collection added successfully: {collection_name}")
        except Exception as e:
            logger.error(
                f"Failed to add collection {collection_name}: {e}", exc_info=True
            )
            raise

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection from the remote vector store."""
        try:
            logger.debug(f"Deleting collection: {collection_name}")
            # This one is already correct - uses params
            response = self._delete("collections", {"collection_name": collection_name})
            self._handle_response(
                response,
                f"Collection {collection_name} deleted successfully.",
                "Failed to delete collection",
            )
            logger.info(f"Collection deleted successfully: {collection_name}")
        except Exception as e:
            logger.error(
                f"Failed to delete collection {collection_name}: {e}", exc_info=True
            )
            raise

    def get_collections(self) -> List[str]:
        """Lists all collections in the remote vector store."""
        try:
            logger.debug("Retrieving collections list")
            response = self._get("collections")
            data = self._handle_response(
                response, error_message="Failed to list collections"
            )
            if "items" not in data:
                raise Exception("Invalid response format: 'items' key missing.")
            collections = data["items"]
            logger.info(f"Retrieved collections - count: {len(collections)}")
            return collections
        except Exception as e:
            logger.error(f"Failed to retrieve collections: {e}", exc_info=True)
            return []

    # Helper methods remain the same
    def _handle_response(
        self,
        response,
        success_message: str = None,
        error_message: str = "Request failed",
    ):
        """Common response handling logic."""
        if response.status_code != 200:
            logger.error(
                f"HTTP request failed - status: {response.status_code}, error: {error_message}"
            )
            raise Exception(f"{error_message}: {response.text}")

        data = response.json()
        if success_message and data.get("success"):
            logger.debug(success_message)

        return data

    def _get(self, call: str, data: Optional[dict] = None):
        logger.debug(f"GET request - endpoint: {self.url}/{call}, params: {data}")
        return requests.get(
            f"{self.url}/{call}",
            headers=self._get_headers(),
            params=data,
        )

    def _post(self, call: str, data: dict = None, params: dict = None):
        """Updated _post method to support both JSON body and query params."""
        logger.debug(
            f"POST request - endpoint: {self.url}/{call}, data: {data}, params: {params}"
        )
        return requests.post(
            f"{self.url}/{call}",
            headers=self._get_headers(),
            json=data if data is not None else None,
            params=params,
        )

    def _delete(self, call: str, data: Optional[dict] = None):
        logger.debug(f"DELETE request - endpoint: {self.url}/{call}, params: {data}")
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
