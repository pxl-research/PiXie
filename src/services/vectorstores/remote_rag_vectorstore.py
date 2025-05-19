from services.abstractclasses.vectorstore import VectorStore
from langchain_core.documents import Document
from typing import List
import requests
import os
import logging


class RemoteRagVectorStore(VectorStore):
    def __init__(self, url: str):
        self.url = url

    def add_document(
        self, collection_name: str, file_name: str, chunks: List[Document]
    ) -> None:
        """
        Adds a document to the remote vector store.
        Args:
            collection_name (str): The name of the collection to add the document to.
            file_name (str): The name of the file to add.
            chunks (List[Document]): The document chunks to add.
        """

        for chunk in chunks:
            chunk.metadata["file_name"] = file_name
        try:
            # Convert Document objects to dictionaries for JSON serialization
            serializable_chunks = [
                {"page_content": chunk.page_content, "metadata": chunk.metadata}
                for chunk in chunks
            ]
            response = self._post(
                "add_document",
                {
                    "collection_name": collection_name,
                    "document_name": file_name,
                    "chunks": serializable_chunks,
                },
            )
            if response.status_code != 200:
                raise Exception(f"Failed to add document: {response.text}")
            logging.info(f"Document {file_name} added to {collection_name}.")
        except Exception as e:
            logging.error(f"Failed to add document {file_name}: {str(e)}")
            raise

    def delete_document(self, collection_name: str, file_name: str) -> bool:
        """
        Deletes a document from the remote vector store.

        Args:
            doc_title (str): The title of the document to delete.
        """

        try:
            response = self._get(
                "delete_document",
                {
                    "collection_name": collection_name,
                    "document_name": file_name,
                },
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

    def list_collections(self) -> List[str]:
        """
        Lists all collections in the remote vector store.

        Returns:
            List[str]: A list of collection names.
        """
        response = self._get("list_collections")
        if response.status_code != 200:
            raise Exception(f"Failed to list collections: {response.text}")

        data = response.json()
        if "items" not in data:
            raise Exception("Invalid response format: 'collections' key missing.")
        return data["items"]

    def add_collection(self, collection_name):
        """
        Adds a collection to the remote vector store.

        Args:
            collection_name (str): The name of the collection to add.
        """
        response = self._get("add_collection", {"collection_name": collection_name})
        if response.status_code != 200:
            raise Exception(f"Failed to add collection: {response.text}")
        logging.info(f"Collection {collection_name} added.")

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

    def is_doc_up_to_date_in_list(self, file_hast: str, collection_name: str) -> bool:
        """
        Checks if a document is up to date in the list.

        Args:
            collection_name (str): The name of the collection.
            file_name (str): The name of the document.

        Returns:
            bool: True if the document is up to date, False otherwise.
        """
        response = self._get(
            "is_doc_up_to_date",
            {"file_hash": file_hast, "collection_name": collection_name},
        )
        if response.status_code != 200:
            raise Exception(f"Failed to check document status: {response.text}")
        return response.json().get("success", False)

    def is_doc_in_list(self, file_name: str, collection_name: str) -> bool:
        """
        Checks if a document is in the list.

        Args:
            collection_name (str): The name of the collection.
            file_name (str): The name of the document.

        Returns:
            bool: True if the document is in the list, False otherwise.
        """
        response = self._get(
            "is_doc_in_list",
            {"file_name": file_name, "collection_name": collection_name},
        )
        if response.status_code != 200:
            raise Exception(f"Failed to check document status: {response.text}")
        return response.json().get("success", False)

    def get_doc_list(self, collection_name: str) -> List[str]:
        """
        Retrieves the list of documents in a collection.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            List[str]: A list of document names.
        """
        response = self._get("get_doc_list", {"collection_name": collection_name})
        if response.status_code != 200:
            raise Exception(f"Failed to get document list: {response.text}")
        return response.json().get("items", [])

    def add_to_doc_list(self, file_name: str, collection_name: str) -> bool:
        """
        Adds a document to the list.

        Args:
            file_name (str): The name of the document.
            collection_name (str): The name of the collection.

        Returns:
            bool: True if the document was added successfully, False otherwise.
        """
        response = self._get(
            "add_to_doc_list",
            {"file_name": file_name, "collection_name": collection_name},
        )
        if response.status_code != 200:
            raise Exception(f"Failed to add document to list: {response.text}")
        return response.json().get("success", False)

    def remove_from_doc_list(self, file_name: str, collection_name: str) -> bool:
        """
        Deletes a document from the list.

        Args:
            file_name (str): The name of the document.
            collection_name (str): The name of the collection.

        Returns:
            bool: True if the document was deleted successfully, False otherwise.
        """
        response = self._get(
            "remove_from_doc_list",
            {"file_name": file_name, "collection_name": collection_name},
        )
        if response.status_code != 200:
            raise Exception(f"Failed to delete document from list: {response.text}")
        return response.json().get("success", False)

    def _get(self, call: str, data: dict | None = None):
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
