import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from services.abstractclasses.embedding_model import EmbeddingModel

# TODO: inherit from Splitter, but this needs changes from list[str] to list[Document]
# This puts a hard dependency on LangChain though, 
# is this something we want or should we use our own Document class or dataclass?
class SemanticTextSplitter:
    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model

    def _split_into_sentences(self, text: str) -> list[str]: 
        # Split text into sentences via punctuation followed by whitespace.
        return re.split(r"(?<=[.?!])\s+", text)    
        
    def _combine_into_windowed_sentences(self, sentences: list[str]) -> list[str]: 
        # Combine successive sentences into a triplet, e.g. sentences 
        # (replace sentence number by text in your mind):
        # [0,1,2],[1,2,3],[2,3,4],...
        return (
            [" ".join(sentences)] if len(sentences) <= 2
            else [f"{sentences[i-1]} {sentence} {sentences[i+1]}" 
                for i, sentence in enumerate(sentences[1:-1], 1)
            ]
        )
        
    def _texts_to_embeddings(self, texts: list[str], normalize: bool = False) -> np.ndarray:
        try:
            return self.embedding_model.embed_documents(texts, normalize, to_list=False)
        except Exception as e:
            print("An error occurred:", e)
        return np.array([])  # empty array  

    def _merge(self, single_sentences_list: list[str], similarities: list[float], 
               breakpoint_percentile_threshold: int = 70) -> list[str]:
        # distance below which 30% of the distances fall
        breakpoint_distance_threshold = np.percentile(similarities, 100 - breakpoint_percentile_threshold)
        # Find all indices where similarities are below threshold, indicating a split.
        indices_below_thresh = [ 
            i for i, s in enumerate(similarities) if s < breakpoint_distance_threshold
        ]

        chunks = []
        start_index = 0 # start index of the next chunk
        for index in indices_below_thresh:
            chunk = ' '.join(single_sentences_list[start_index:index+1])
            chunks.append(chunk)
            start_index = index + 1
        
        # For sentences left after the last breakpoint: add them as final chunk
        if start_index < len(single_sentences_list):
            chunk = ' '.join(single_sentences_list[start_index:])
            chunks.append(chunk)
        return chunks

    def split_text(self, text: str) -> list[str]:
        # Cosine similarities of successive embeddings
        cosine_similarities_successive_embeddings = (
            lambda embeddings: [
                cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
                for i in range(len(embeddings) - 1)
            ]
        )
        
        # Full semantic chunking pipeline
        single_sentences_list = self._split_into_sentences(text)
        combined_sentences = self._combine_into_windowed_sentences(single_sentences_list)
        embeddings = self._texts_to_embeddings(combined_sentences)
        similarities = cosine_similarities_successive_embeddings(embeddings)
        chunks = self._merge(single_sentences_list, similarities, breakpoint_percentile_threshold=70)
        
        # TODO: overlap of successive chunks (e.g. of 20% of the tokens)
        # TODO: maximal (e.g. 1024 tokens of embedding model) chunk lengths
        
        return chunks
