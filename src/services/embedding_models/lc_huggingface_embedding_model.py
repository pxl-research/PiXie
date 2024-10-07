from typing import Any, Optional, Union
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

from services.abstractclasses.embedding_model import EmbeddingModel

class LangChainHuggingFaceEmbeddingModel(EmbeddingModel):
    def __init__(self, model_name: str, model_kwargs: Optional[dict[str, Any]], cache_folder: Optional[str] = None):
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs if model_kwargs is not None else {"device": "cpu"},
            cache_folder=cache_folder,
        )
        
    def tokenizer_encode(self, text: str) -> list[int]:
        tokenizer = self.embeddings.client.tokenizer
        tokens = tokenizer.encode(text, add_special_tokens=False)
        return tokens
    
    def tokenizer_decode(self, tokens: list[int]) -> str:
        tokenizer = self.embeddings.client.tokenizer
        text = tokenizer.decode(tokens)
        return text
    
    def embed_documents(self, texts: list[str], 
                        normalize: bool = False, to_list: bool = True) -> Union[list[list[float]], np.ndarray]:
        embedding_vectors = self.embeddings.embed_documents(texts)
        x = np.array(embedding_vectors)
        if normalize:
            x = x / np.linalg.norm(x, axis=1, keepdims=True)
        if to_list:
            return x.tolist()
        return x
    
    def embed_query(self, text: str, normalize: bool = False, to_list: bool = True) -> Union[list[float], np.ndarray]:
        embedding_vector = self.embeddings.embed_query(text)
        x = np.array(embedding_vector)
        if normalize:
            x = x / np.linalg.norm(x)
        if to_list:
            return x.tolist()
        return x
    
    def get_embedding_vector_dimension(self) -> int:
        return self.embeddings.client._first_module().auto_model.config.hidden_size
    
    def get_max_token_count(self) -> int:
        return self.embeddings.client._first_module().auto_model.config.max_position_embeddings 
    
    def get_embeddings(self) -> Any:
        return self.embeddings