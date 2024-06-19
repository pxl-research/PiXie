from abc import ABC, abstractmethod

import os
from FlagEmbedding import FlagReranker


class Reranker(ABC):
    """
    Abstract base class for a retriever.
    """

    @abstractmethod
    def rerank(self, question, docs):
        """
        Abstract method to retrieve chunks from a vector store.
        """
        pass


class BGEReranker(Reranker):

    def rerank(self, question, docs):

        reranker = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=True)
        page_contents = [(question, doc.page_content) for doc in docs]
        scores = reranker.compute_score(page_contents)

        top_docs = sorted(docs, key=lambda doc: scores[docs.index(doc)], reverse=True)[
            :3
        ]

        return top_docs
