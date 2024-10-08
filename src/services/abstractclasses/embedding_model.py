from abc import ABC, abstractmethod
from typing import Any, Union
import numpy as np


class EmbeddingModel(ABC):
    @abstractmethod
    def tokenizer_encode(self, text: str) -> list[int]:
        pass

    @abstractmethod
    def tokenizer_decode(self, tokens: list[int]) -> str:
        pass

    @abstractmethod
    def embed_documents(
        self, texts: list[str], normalize: bool = False, to_list: bool = True
    ) -> Union[list[list[float]], np.ndarray]:
        pass

    @abstractmethod
    def embed_query(
        self, text: str, normalize: bool = False, to_list: bool = True
    ) -> Union[list[float], np.ndarray]:
        pass

    @abstractmethod
    def get_embedding_vector_dimension(self) -> int:
        pass

    @abstractmethod
    def get_max_token_count(self) -> int:
        pass

    @abstractmethod
    def get_embeddings(self) -> Any:
        pass
