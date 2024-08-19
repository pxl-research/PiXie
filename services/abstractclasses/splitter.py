from abc import ABC, abstractmethod
from typing import List, Union
from langchain_core.documents import Document


class Splitter(ABC):
    """
    Abstract base class for a text splitter.
    """

    @abstractmethod
    def split(self, docs: List[Document]) -> List[Document]:
        """
        Abstract method to split a list of text documents into chunks.

        Args:
            docs (List[Document]): A list of documents to be split.

        Returns:
            List[Document]: A list of split document chunks.
        """
        pass
