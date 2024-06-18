from services.document_loader import AzureDocumentLoader
from services.splitter import CustomMarkdownSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
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
encode_kwargs = {"normalize_embeddings": False}
embeddings = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs,
    cache_folder="embeddings",
)

vector_store = QDrantVectorStore("pixie", embeddings, "https://eef1fb63-69f7-41a2-b729-bed9f225b926.us-east4-0.gcp.cloud.qdrant.io", 6333)

reranker = BGEReranker()

llm = GPT35(0)
chain = Chain()