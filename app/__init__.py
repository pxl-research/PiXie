from services.document_loader import AzureDocumentLoader
from services.splitter import CustomMarkdownSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from services.vectorstore import QDrantVectorStore
from services.reranker import BGEReranker
from services.llm import GPT35
from services.chat import Chain

import os
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

document_loader = AzureDocumentLoader()
splitter = CustomMarkdownSplitter(header_depth=3, chunk_size=512, chunk_overlap=128)

model_kwargs = {"device": "cpu"}
embeddings = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDINGS_MODEL_NAME"),
    model_kwargs=model_kwargs,
    cache_folder="embeddings",
)


vector_store = QDrantVectorStore(
    "pixie",
    embeddings,
    os.getenv("QDRANT_URL"),
    6333,
)

reranker = BGEReranker()

llm = GPT35(0)
chain = Chain()
