from typing import Any, Optional, Union
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

from services.abstractclasses import EmbeddingModel


class HuggingFaceEmbeddingModel(EmbeddingModel):
    def __init__(
        self,
        model_name: str,
        model_kwargs: Optional[dict[str, Any]],
        cache_dir: Optional[str] = None,
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        model_kwargs = model_kwargs if model_kwargs is not None else {"device": "cpu"}
        device = torch.device(model_kwargs["device"])
        self.model = AutoModel.from_pretrained(model_name, cache_dir=cache_dir).to(
            device
        )

    def tokenizer_encode(self, text: str) -> list[int]:
        return self.tokenizer.encode(text, add_special_tokens=False)

    def tokenizer_decode(self, tokens: list[int]) -> str:
        return self.tokenizer.decode(tokens, skip_special_tokens=True)

    def embed_documents(
        self, texts: list[str], normalize: bool = False, to_list: bool = True
    ) -> Union[list[list[float]], np.ndarray]:
        encoded_input = self.tokenizer(
            texts, padding=True, truncation=True, return_tensors="pt"
        )
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            # Perform pooling to aggregate token embedding vectors to sentence embedding vector
            # We go from a sequence of embedding vectors to 1 embedding vector
            # https://blog.ml6.eu/the-art-of-pooling-embeddings-c56575114cf8
            embedding_vectors = model_output[0][:, 0].cpu()  # CLS pooling
            # Each sentence starts with CLS token
            # We take the embedding vector of the CLS token, which captures the sentence information (highly compressed)
            # During training, some sentence-level classification task based on this CLS embedding
            # will tune the CLS token representation via backpropagation.
            # e.g. In BERT’s pre-training process, this task is NSP (Next Sentence Prediction).

            # normalize embeddings
            if normalize:
                embedding_vectors = torch.nn.functional.normalize(
                    embedding_vectors, p=2, dim=1
                )
            result = embedding_vectors.numpy()
            result = result.flatten() if result.shape[0] == 1 or result.shape[1] == 1 else result
            if to_list:
                return result.tolist()

        return result

    def embed_query(
        self, text: str, normalize: bool = False, to_list: bool = True
    ) -> Union[list[float], np.ndarray]:
        embedding_vector = self.embed_documents([text], normalize, to_list)
        return embedding_vector

    def get_embedding_vector_dimension(self) -> int:
        return self.model.config.hidden_size

    def get_max_token_count(self) -> int:
        return self.model.config.max_position_embeddings

    def get_embeddings(self) -> tuple[AutoTokenizer, AutoModel]:
        return self.tokenizer, self.model
