import logging
from typing import Optional, List

import os
import pandas as pd
import requests
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class RemoteTabularVectorStore:
    """
    Postgres pgvector implementation of a TabularVectorStore working on tabular data.
    """

    def __init__(self, url: str):
        self.url = url
        logger.debug(f"Initialized RemoteTabularVectorStore with URL: {url}")

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
        Deletes one or more tabular documents from the tabular pgvector vector store
        based on the collection and file name or file name pattern.

        Args:
            collection_name (str): The name of the collection the document(s) belong to.
            file_name (str): The name or pattern of the files to delete.

        Returns:
            bool: True if at least one document was deleted, False otherwise.
        """
        try:
            logger.debug(
                f"Deleting document - collection: {collection_name}, file: {file_name}"
            )
            response = self._delete(
                f"collections/{collection_name}/documents", {"file_name": file_name}
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
        """Retrieves a list of document file names in a collection."""
        try:
            logger.debug(f"Retrieving documents - collection: {collection_name}")
            response = self._get(f"collections/{collection_name}/documents")
            data = self._handle_response(
                response, error_message="Failed to list documents"
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

    def document_version_exists(self, file_hash: str, collection_name: str) -> bool:
        """Check if a document version (hash) is up-to-date in the collection."""
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

    def get_collections(self) -> List[str]:
        """Lists all collections in the tabular pgvector vector store."""
        try:
            logger.debug("Retrieving collections list")
            response = self._get("collections")
            data = self._handle_response(
                response, error_message="Failed to list collections"
            )
            collections = data.get("items", [])
            logger.info(f"Retrieved collections - count: {len(collections)}")
            return collections
        except Exception as e:
            logger.error(f"Failed to retrieve collections: {e}", exc_info=True)
            return []

    def add_collection(self, collection_name: str) -> None:
        """Adds a collection to the tabular pgvector vector store."""
        try:
            logger.debug(f"Adding collection: {collection_name}")
            # Send collection_name as query parameter instead of JSON body
            response = self._post(
                "collections", data=None, params={"collection_name": collection_name}
            )
            data = self._handle_response(
                response,
                f"Collection {collection_name} added successfully.",
                "Failed to add collection",
            )
            if not data.get("success"):
                logger.info(f"Collection already exists: {collection_name}")
            else:
                logger.info(f"Collection added successfully: {collection_name}")
        except Exception as e:
            logger.error(
                f"Failed to add collection {collection_name}: {e}", exc_info=True
            )
            raise

    def delete_collection(self, collection_name: str) -> None:
        """
        Deletes a collection and its associated relations from the tabular pgvector vector store.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        try:
            logger.debug(f"Deleting collection: {collection_name}")
            response = self._delete("collections", {"collection_name": collection_name})
            data = self._handle_response(
                response,
                f"Collection {collection_name} deleted successfully.",
                "Failed to delete collection",
            )
            if not data.get("success"):
                logger.info(f"Collection does not exist: {collection_name}")
            else:
                logger.info(f"Collection deleted successfully: {collection_name}")
        except Exception as e:
            logger.error(
                f"Failed to delete collection {collection_name}: {e}", exc_info=True
            )
            raise

    def get_summaries(self, collection_name: str) -> List[str]:
        """Retrieves file descriptions for a collection."""
        try:
            logger.debug(f"Retrieving summaries - collection: {collection_name}")
            response = self._get(f"collections/{collection_name}/summaries")
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
            logger.debug(
                f"Retrieving top rows - collection: {collection_name}, question_length: {len(question)}, top_k: {top_k}"
            )
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
            result_df = pd.DataFrame(data["data"])
            logger.info(
                f"Retrieved top rows - collection: {collection_name}, rows: {len(result_df)}"
            )
            return result_df
        except Exception as e:
            logger.error(
                f"Failed to retrieve top rows - collection: {collection_name}: {e}",
                exc_info=True,
            )
            raise

    # Helper methods
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

    def get_allowed_entities(self, collection_name: str) -> list[str]:
        """
        Returns a list of allowed entities for the tabular vector store.
        This is a placeholder method and should be implemented based on actual requirements.
        """
        response = requests.get(
            f"{self.url}/collections/{collection_name}/products",
            headers=self._get_headers(),
        )

        data = self._handle_response(
            response,
            error_message="Failed to retrieve allowed entities",
        )
        products = data.get("items", [])

        return products

    def get_recommended_table(
        self, question: str, collection_name: str
    ) -> tuple[str, list[str]]:
        """
        Retrieves a recommended table based on the question and collection name.
        This is a placeholder method and should be implemented based on actual requirements.
        """
        response = requests.post(
            f"{self.url}/recommend-table",
            headers=self._get_headers(),
            params={"question": question, "collection_name": collection_name},
        )

        data = self._handle_response(
            response,
            error_message="Failed to retrieve recommended table",
        )
        table_name = data.get("table_name", "")
        columns = data.get("column_names", [])

        return table_name, columns

    def product_search(
        self, collection_name: str, product_name: str, question: str, top_k: int = 3
    ) -> list[dict[str, dict[str, Any]]]:
        """
        Searches for products in the specified collection based on the product name and question.

        Args:
            collection_name (str): The name of the collection to search within.
            product_name (str): The name of the product to search for.
            question (str): The question related to the product.
            top_k (int, optional): Number of top results to return. Default is 3.

        Returns:
            list[dict[str, dict[str, Any]]]: List of products with their attributes.
        """
        print(
            f">>>DEBUG>>> Searching for product: {product_name} in collection: {collection_name} with question: {question}"
        )
        print(
            f"{self.url}/collections/{collection_name}/products/{product_name}/search"
        )
        if "#" in product_name:
            # Excel file with sheet name: extract part after #
            product = product_name.split("#")[-1]
        else:
            # Regular product name: use as is
            product = product_name
        print(f">>>DEBUG>>> Cleaned product name: {product}")
        response = requests.get(
            f"{self.url}/collections/{collection_name}/products/{product}/search",
            headers=self._get_headers(),
            params={
                "question": question,
                "top_k": top_k,
            },
        )

        data = self._handle_response(
            response, error_message="Failed to search products"
        )
        return data.get("data", [])
