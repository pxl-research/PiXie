# vector_store.py
from typing import List
from abc import ABC, abstractmethod
from langchain_core.documents import Document


class VectorStore(ABC):
    """
    Abstract base class for a vector store.
    """

    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def add_document(
        self, collection_name: str, file_name: str, chunks: List[Document]
    ) -> None:
        """
        Abstract method to add a document to the vector store.

        Args:
            collection_name (str): The name of the collection to add the document to.
            file_name (str): The name of the file to add.
            chunks (List[Document]): The document chunks to add.
        """
        pass

    @abstractmethod
    def delete_document(self, collection_name: str, file_name: str) -> None:
        """
        Abstract method to delete a document from the vector store.

        Args:
            collection_name (str): The name of the collection to delete the document from.
            file_name (str): The title of the document to delete.
        """
        pass

    @abstractmethod
    def retrieve_top_chunks(
        self, collection_name: str, question: str, k: int
    ) -> List[Document]:
        """
        Abstract method to retrieve the top K most similar document chunks to the given question.

        Args:
            question (str): The query to search for.
            k (int): The number of top results to return.

        Returns:
            List[Document]: A list of the top K similar documents.
        """
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
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
