from services.document_loaders.azure_document_loader import AzureDocumentLoader #DoclingDocumentLoader
from services.splitters.custom_markdown_splitter import CustomMarkdownSplitter
from services.embedding_models.lc_huggingface_embedding_model import (
    LangChainHuggingFaceEmbeddingModel,
)
from services.vectorstores.qdrant_vectorstore import QDrantVectorStore
from services.rerankers.bge_reranker import BGEReranker
from services.llms.azure_openai_llm import AzureOpenAILLM
from services.llm_chain_service import LLMChainBuilder
from services.summarizer import Summarizer

import os
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

document_loader = AzureDocumentLoader(
    api_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
    api_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
)

#document_loader = DoclingDocumentLoader()

splitter = CustomMarkdownSplitter(header_depth=3, chunk_size=512, chunk_overlap=128)

model_kwargs = {"device": os.getenv("DEVICE_TYPE", "cpu")}
embeddings_model = LangChainHuggingFaceEmbeddingModel(
    model_name=os.getenv("EMBEDDINGS_MODEL_NAME"),
    model_kwargs=model_kwargs,
    cache_folder="embeddings_cache",
)

vector_store = QDrantVectorStore(
    embeddings=embeddings_model.get_embeddings(),
    host=os.getenv("QDRANT_HOST"),
    port=os.getenv("QDRANT_PORT"),
)

reranker = BGEReranker()

llm = AzureOpenAILLM(
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    model_version=os.getenv("AZURE_OPENAI_MODEL_VERSION"),
)

chain_builder = LLMChainBuilder(llm)

summarizer = Summarizer(llm)
