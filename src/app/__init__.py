from services.document_loaders.document_loader_manager import (
    ConfigurableDocumentProcessingManager,
)
from services.splitters.custom_markdown_splitter import CustomMarkdownSplitter
from services.embedding_models.lc_huggingface_embedding_model import (
    LangChainHuggingFaceEmbeddingModel,
)
from services.vectorstores.qdrant_vectorstore import QDrantVectorStore
from services.rerankers.bge_reranker import BGEReranker
from services.llms.azure_openai_llm import AzureOpenAILLM
from services.llm_chain_service import LLMChainBuilder
from services.summarizer import Summarizer
from services.vectorstores.tabular_pg_vectorstore import TabularPGVectorStore
from services.llms.tabular_summarizer_llm import TabularSummarizerLLM
from services.llms.tabular_where_filter_generator_llm import TabularWhereFilterGeneratorLLM

import os
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

file_to_strategy = {
    "docx": os.getenv("DOCX_STRATEGY"),
    "doc": os.getenv("DOCX_STRATEGY"),
    #"odt": os.getenv("DOCX_STRATEGY"),
    #"rtf": os.getenv("DOCX_STRATEGY"),
    "pdf": os.getenv("PDF_STRATEGY"),
    "pptx": os.getenv("PPTX_STRATEGY"),
    #"odp": os.getenv("PPTX_STRATEGY"),
    "csv": os.getenv("CSV_STRATEGY"),
    "xlsx": os.getenv("XLSX_STRATEGY"),
    "xls": os.getenv("XLSX_STRATEGY"),
    #"ods": os.getenv("XLSX_STRATEGY"),
    #"md": os.getenv("MD_STRATEGY"),
}

document_loader = ConfigurableDocumentProcessingManager(file_to_strategy)

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

tabular_summarizer_llm = TabularSummarizerLLM(llm=llm)
tabular_where_filter_generator_llm = TabularWhereFilterGeneratorLLM(llm=llm)

tabular_vector_store = TabularPGVectorStore( 
    embedding_model=embeddings_model,
    tabular_where_filter_generator_llm=tabular_where_filter_generator_llm
)