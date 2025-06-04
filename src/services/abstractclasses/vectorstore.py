# vector_store.py
from typing import List
from abc import ABC, abstractmethod


class VectorStore(ABC):
    """
    Abstract base class for a vector store.
    """

    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def add_document(
        self, collection_name: str, file_path: str, file_hash: str
    ) -> None:
        """
        Abstract method to add a document to the vector store.

        Args:
            collection_name (str): The name of the collection to add the document to.
            file_path (str): The path to the file to add.
            file_hash (str): The hash of the file.
        """
        pass

    @abstractmethod
    def delete_document(self, collection_name: str, file_name: str) -> bool:
        """
        Abstract method to delete a document from the vector store.

        Args:
            collection_name (str): The name of the collection to delete the document from.
            file_name (str): The name of the document to delete.
            
        Returns:
            bool: True if the document was successfully deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_documents(self, collection_name: str) -> List[str]:
        """
        Abstract method to retrieve the list of documents in a collection.
        
        Args:
            collection_name (str): The name of the collection.
            
        Returns:
            List[str]: A list of document names in the collection.
        """
        pass

    @abstractmethod
    def document_exists(self, collection_name: str, file_name: str) -> bool:
        """
        Abstract method to check if a document exists in the collection.
        
        Args:
            collection_name (str): The name of the collection.
            file_name (str): The name of the document to check.
            
        Returns:
            bool: True if the document exists, False otherwise.
        """
        pass

    @abstractmethod
    def document_version_exists(self, collection_name: str, file_hash: str) -> bool:
        """
        Abstract method to check if a document version (hash) exists in the collection.
        
        Args:
            collection_name (str): The name of the collection.
            file_hash (str): The hash of the document to check.
            
        Returns:
            bool: True if the document version exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_collections(self) -> List[str]:
        """
        Abstract method to list all collections in the vector store.

        Returns:
            List[str]: A list of collection names.
        """
        pass

    @abstractmethod
    def add_collection(self, collection_name: str) -> None:
        """
        Abstract method to add a collection to the vector store.

        Args:
            collection_name (str): The name of the collection to add.
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_name: str) -> None:
        """
        Abstract method to delete a collection from the vector store.

        Args:
            collection_name (str): The name of the collection to delete.
        """
        pass
