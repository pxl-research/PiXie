from abc import ABC, abstractmethod
from typing import List
from langchain_core.documents import Document


class Reranker(ABC):
    """
    Abstract base class for a reranker.
    """

    @abstractmethod
    def rerank(self, question: str, docs: List[Document], top_k: int) -> List[Document]:
        """
        Abstract method to rerank documents based on their relevance to a question.

        Args:
            question (str): The query or question to rerank the documents for.
            docs (List[Document]): The list of documents to rerank.
            top_k (int): The number of top documents to return.

        Returns:
            List[Document]: A list of the top-k documents ranked by their relevance to the question.
        """
        pass
