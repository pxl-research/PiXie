from typing import List
import re
import numpy as np
from langchain_core.documents import Document

from services.abstractclasses.splitter import Splitter
from services.abstractclasses.embedding_model import EmbeddingModel


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


class SemanticTextSplitter(Splitter):
    def __init__(
        self, embedding_model: EmbeddingModel, breakpoint_percentile_threshold: int = 70
    ):
        self.embedding_model = embedding_model
        self.breakpoint_percentile_threshold = breakpoint_percentile_threshold

    def _split_into_sentences(self, text: str) -> List[str]:
        # Split text into sentences via punctuation followed by whitespace.
        return re.split(r"(?<=[.?!])\s+", text)

    def _combine_into_windowed_sentences(self, sentences: List[str]) -> List[str]:
        # Combine successive sentences into a triplet, e.g. sentences
        # (replace sentence number by text in your mind):
        # [0,1,2],[1,2,3],[2,3,4],...
        return (
            [" ".join(sentences)]
            if len(sentences) <= 2
            else [
                f"{sentences[i-1]} {sentence} {sentences[i+1]}"
                for i, sentence in enumerate(sentences[1:-1], 1)
            ]
        )

    def _texts_to_embeddings(
        self, texts: List[str], normalize: bool = False
    ) -> np.ndarray:
        try:
            return self.embedding_model.embed_documents(texts, normalize, to_list=False)
        except Exception as e:
            print("An error occurred:", e)
        return np.array([])  # empty array

    def _merge(
        self,
        single_sentences_list: List[str],
        similarities: List[float],
        breakpoint_percentile_threshold: int = 70,
    ) -> List[str]:
        # distance below which 30% of the distances fall
        breakpoint_distance_threshold = np.percentile(
            similarities, 100 - breakpoint_percentile_threshold
        )
        # Find all indices where similarities are below threshold, indicating a split.
        indices_below_thresh = [
            i for i, s in enumerate(similarities) if s < breakpoint_distance_threshold
        ]

        chunks = []
        start_index = 0  # start index of the next chunk
        for index in indices_below_thresh:
            chunk = " ".join(single_sentences_list[start_index : index + 1])
            chunks.append(chunk)
            start_index = index + 1

        # For sentences left after the last breakpoint: add them as final chunk
        if start_index < len(single_sentences_list):
            chunk = " ".join(single_sentences_list[start_index:])
            chunks.append(chunk)
        return chunks

    def split(self, docs: List[Document]) -> List[Document]:
        # Cosine similarities of successive embeddings
        cosine_similarities_successive_embeddings = lambda embeddings: [
            cosine_similarity([embeddings[i]], [embeddings[i + 1]])
            for i in range(len(embeddings) - 1)
        ]

        # Full semantic chunking pipeline
        doc_chunks = []
        for doc in docs:
            text = doc.page_content
            metadata = doc.metadata

            single_sentences_list = self._split_into_sentences(text)
            combined_sentences = self._combine_into_windowed_sentences(
                single_sentences_list
            )
            embeddings = self._texts_to_embeddings(combined_sentences)
            similarities = cosine_similarities_successive_embeddings(embeddings)
            chunks = self._merge(
                single_sentences_list,
                similarities,
                breakpoint_percentile_threshold=self.breakpoint_percentile_threshold,
            )
            doc_chunks += [
                Document(page_content=chunk, metadata=metadata) for chunk in chunks
            ]

        return doc_chunks
