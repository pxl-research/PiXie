# vector_store.py
import logging
from typing import List
from abc import ABC, abstractmethod
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document


class VectorStore(ABC):
    """
    Abstract base class for a vector store.
    """

    def __init__(self, collection_name: str, embeddings: Embeddings):
        self.collection_name = collection_name
        self.embeddings = embeddings

    @abstractmethod
    def add_document(self, file_name: str, chunks: List[Document]) -> None:
        """
        Abstract method to add a document to the vector store.

        Args:
            file_name (str): The name of the file to add.
            chunks (List[Document]): The document chunks to add.
        """
        pass

    @abstractmethod
    def delete_document(self, doc_title: str) -> None:
        """
        Abstract method to delete a document from the vector store.

        Args:
            doc_title (str): The title of the document to delete.
        """
        pass

    @abstractmethod
    def retrieve_top_chunks(self, question: str, k: int) -> List[Document]:
        """
        Abstract method to retrieve the top K most similar document chunks to the given question.

        Args:
            question (str): The query to search for.
            k (int): The number of top results to return.

        Returns:
            List[Document]: A list of the top K similar documents.
        """
        pass
