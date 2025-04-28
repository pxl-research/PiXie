from typing import List
from FlagEmbedding import FlagReranker
from langchain_core.documents import Document
from services.abstractclasses.reranker import Reranker
import time
import torch


class BGEReranker(Reranker):
    """
    Reranker implementation using the BAAI/bge-reranker-v2-m3 model.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        use_fp16: bool = True,
        cache_dir: str = "/app/reranker_cache",
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        batch_size: int = 16,
    ):
        """
        Initialize the BGEReranker with a specific model.

        Args:
            model_name (str): The name of the model to use for reranking.
            use_fp16 (bool): Whether to use FP16 precision for faster computation.
            device (str): Device to run the model on, e.g., 'cpu' or 'cuda'.
            batch_size (int): Batch size to use during scoring.
        """
        self.device = device
        self.batch_size = batch_size
        self.reranker = FlagReranker(
            model_name,
            use_fp16=use_fp16,
            cache_dir=cache_dir,
            device=device
        )

    def rerank(self, question: str, docs: List[Document], top_k: int) -> List[Document]:
        import logging
        logger = logging.getLogger(__name__)

        """
        Reranks the documents based on their relevance to the question.
        """
        start_time = time.perf_counter()

        page_contents = [(question, doc.page_content) for doc in docs]
        logger.info(f"[BENCHMARK] Device used for reranking: {self.device}, Batch size: {self.batch_size}")
        scores = self.reranker.compute_score(page_contents, batch_size=self.batch_size)

        duration = time.perf_counter() - start_time
        logger.info(f"[BENCHMARK] Reranking {len(docs)} documents took {duration:.4f} seconds.")

        # Associate documents with their scores and sort
        scored_docs = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

        # Return the top_k documents
        top_docs = [doc for doc, score in scored_docs[:top_k]]

        return top_docs
