from typing import Any, Optional, Union
import numpy as np
from langchain_openai import AzureOpenAIEmbeddings
import tiktoken

from services.abstractclasses.embedding_model import EmbeddingModel


class LangChainAzureOpenAIEmbeddingModel(EmbeddingModel):
    def __init__(
        self,
        model: str,
        azure_endpoint: str,
        api_key: str,
        openai_api_version: str,
        dimensions: Optional[int] = None,
    ):
        self.embeddings = AzureOpenAIEmbeddings(
            model=model,
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            openai_api_version=openai_api_version,
        )
        if dimensions is not None:
            self.embeddings.dimensions = dimensions

    def tokenizer_encode(self, text: str) -> list[int]:
        tokenizer = tiktoken.encoding_for_model(self.embeddings.model)
        tokens = tokenizer.encode(text)
        return tokens

    def tokenizer_decode(self, tokens: list[int]) -> str:
        tokenizer = tiktoken.encoding_for_model(self.embeddings.model)
        text = tokenizer.decode(tokens)
        return text

    def embed_documents(
        self, texts: list[str], normalize: bool = False, to_list: bool = True
    ) -> Union[list[list[float]], np.ndarray]:
        embedding_vectors = self.embeddings.embed_documents(texts)
        x = np.array(embedding_vectors)
        if normalize:
            x = x / np.linalg.norm(x, axis=1, keepdims=True)
        if to_list:
            return x.tolist()
        return x

    def embed_query(
        self, text: str, normalize: bool = False, to_list: bool = True
    ) -> Union[list[float], np.ndarray]:
        embedding_vector = self.embeddings.embed_query(text)
        x = np.array(embedding_vector)
        if normalize:
            x = x / np.linalg.norm(x)
        if to_list:
            return x.tolist()
        return x

    def get_embedding_vector_dimension(self) -> int:
        if self.embeddings.model == "text-embedding-ada-002":
            return 1536
        elif self.embeddings.model == "text-embedding-ada-001":
            return 1024
        # These can be specified
        elif self.embeddings.model == "text-embedding-3-large":
            return (
                self.embeddings.dimensions
                if self.embeddings.dimensions is not None
                else 3072
            )
        elif self.embeddings.model == "text-embedding-3-small":
            return (
                self.embeddings.dimensions
                if self.embeddings.dimensions is not None
                else 1536
            )
        else:
            return 1024

    def get_max_token_count(self) -> int:
        return self.embeddings.embedding_ctx_length

    def get_embeddings(self) -> Any:
        return self.embeddings
