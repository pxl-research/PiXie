from typing import List
from FlagEmbedding import FlagReranker
from langchain_core.documents import Document
from services.abstractclasses.reranker import Reranker


class BGEReranker(Reranker):
    """
    Reranker implementation using the BAAI/bge-reranker-v2-m3 model.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        use_fp16: bool = True,
        cache_dir: str = "/app/reranker_cache",
    ):
        """
        Initialize the BGEReranker with a specific model.

        Args:
            model_name (str): The name of the model to use for reranking.
            use_fp16 (bool): Whether to use FP16 precision for faster computation.
        """
        self.reranker = FlagReranker(model_name, use_fp16=use_fp16, cache_dir=cache_dir)

    def rerank(self, question: str, docs: List[Document], top_k: int) -> List[Document]:
        """
        Reranks the documents based on their relevance to the question.

        Args:
            question (str): The query or question to rerank the documents for.
            docs (List[Document]): The list of documents to rerank.
            top_k (int): The number of top documents to return.

        Returns:
            List[Document]: A list of the top-k documents ranked by their relevance to the question.
        """
        page_contents = [(question, doc.page_content) for doc in docs]
        scores = self.reranker.compute_score(page_contents)

        # Associate documents with their scores and sort
        scored_docs = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

        # Return the top_k documents
        top_docs = [doc for doc, score in scored_docs[:top_k]]

        return top_docs
