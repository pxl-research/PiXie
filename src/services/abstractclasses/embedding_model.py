from abc import ABC, abstractmethod
from typing import Any, Union
import numpy as np


class EmbeddingModel(ABC):
    """
    Abstract base class for embedding models, providing a common interface 
    for handling tokenization and embedding vector generation for documents 
    and queries and retrieving model properties 
    such as embedding dimensions and token limits. 
    Implementing classes should provide concrete implementations of these methods.
    """
    @abstractmethod
    def tokenizer_encode(self, text: str) -> list[int]:
        """
        Tokenizes the input text into a list of integer token IDs.

        Args:
            text (str): The input text string to be tokenized.

        Returns:
            list[int]: A list of integer token IDs representing the tokenized text.
        """
        pass

    @abstractmethod
    def tokenizer_decode(self, tokens: list[int]) -> str:
        """
        Decodes a list of integer token IDs back into a string.

        Args:
            tokens (list[int]): A list of token IDs to decode into text.

        Returns: 
            str: The decoded text string.
        """
        pass

    @abstractmethod
    def embed_documents(
        self, texts: list[str], normalize: bool = False, to_list: bool = True
    ) -> Union[list[list[float]], np.ndarray]:
        """
        Generates embeddings for a list of text chunks from a document.

        Args:
            texts (list[str]): A list of chunks to be embedded.
            normalize (bool): Whether to normalize the embedding vectors (default is False).
            to_list (bool): Whether to return embeddings as a list of lists (default is True).
        
        Returns:
            Union[list[list[float]], np.ndarray]: The embeddings for the chunks as a list of lists or 2D numpy array.
        """
        pass

    @abstractmethod
    def embed_query(
        self, text: str, normalize: bool = False, to_list: bool = True
    ) -> Union[list[float], np.ndarray]:
        """
        Generates an embedding for a single query text (for a single text chunk).

        Args:
            text (str): The text chunk to be embedded.
            normalize (bool): Whether to normalize the embedding (default is False).
            to_list (bool): Whether to return the embedding as a list (default is True).
        
        Returns:
            Union[list[float], np.ndarray]: The embedding for the text chunk as a list or numpy array.
        """
        pass

    @abstractmethod
    def get_embedding_vector_dimension(self) -> int:
        """
        Returns the dimensionality of the embedding vector produced by the model.

        Returns:
            int: The dimensionality of the embedding vector.
        """
        pass

    @abstractmethod
    def get_max_token_count(self) -> int:
        """
        Returns the maximum number of tokens that can be processed by the embedding model for a single input.

        Returns:
            int: The maximum token count for the embedding model.
        """
        pass

    @abstractmethod
    def get_embeddings(self) -> Any:
        """
        Returns the underlying embedding model class used directly by some vector store libraries.
        Other vector store libraries might only consume text chunks and embedding vectors more directly.

        Returns:
            Any: The underlying embedding model representation.
        """
        pass
