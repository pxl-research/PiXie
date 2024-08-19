from services.document_loaders.azure_document_loader import AzureDocumentLoader
from services.splitters.custom_markdown_splitter import CustomMarkdownSplitter
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from services.vectorstores.qdrant_vectorstore import QDrantVectorStore
from services.rerankers.bge_reranker import BGEReranker
from services.llms.azure_openai_llm import AzureOpenAILLM
from services.llm_chain_service import LLMChainBuilder

import os
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

document_loader = AzureDocumentLoader(
    api_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
    api_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
)
splitter = CustomMarkdownSplitter(header_depth=3, chunk_size=512, chunk_overlap=128)

model_kwargs = {"device": "cpu"}
embeddings = HuggingFaceEmbeddings(
    model_name=os.getenv("EMBEDDINGS_MODEL_NAME"),
    model_kwargs=model_kwargs,
    cache_folder="embeddings",
)


vector_store = QDrantVectorStore(
    collection_name=os.getenv("QDRANT_COLLECTION_NAME"),
    embeddings=embeddings,
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
