from services.document_loaders.document_loader_manager import (
    ConfigurableDocumentProcessingManager,
)
from services.splitters.custom_markdown_splitter import CustomMarkdownSplitter
from services.embedding_models.lc_huggingface_embedding_model import (
    LangChainHuggingFaceEmbeddingModel,
)
from services.vectorstores.remote_vectorstore import RemoteVectorStore
from services.llms.azure_openai_llm import AzureOpenAILLM
from services.summarizer import Summarizer
from services.vectorstores.tabular_pg_vectorstore import TabularPGVectorStore
from services.llms.tabular_summarizer_llm import TabularSummarizerLLM

import os
import logging

from services.llms.question_queryable_llm import QuestionQueryableLLM
from services.llms.recommendation_sql_post_processor_llm import (
    RecommendationSQLPostProcessorLLM,
)
from services.llms.sql_query_corrector_llm import SQLQueryCorrectorLLM
from services.llms.tabular_sql_query_generator_llm import TabularSQLQueryGeneratorLLM


def create_document_loader():
    """
    Create a document loader manager using file_to_strategy.
    """
    logging.info("Creating document loader manager ...")
    file_to_strategy = {
        "docx": os.getenv("DOCX_STRATEGY"),
        "doc": os.getenv("DOCX_STRATEGY"),
        # "odt": os.getenv("DOCX_STRATEGY"),
        # "rtf": os.getenv("DOCX_STRATEGY"),
        "pdf": os.getenv("PDF_STRATEGY"),
        "pptx": os.getenv("PPTX_STRATEGY"),
        # "odp": os.getenv("PPTX_STRATEGY"),
        "csv": os.getenv("CSV_STRATEGY"),
        "xlsx": os.getenv("XLSX_STRATEGY"),
        "xls": os.getenv("XLSX_STRATEGY"),
        # "ods": os.getenv("XLSX_STRATEGY"),
        # "md": os.getenv("MD_STRATEGY"),
    }
    logging.info("Loaded the file_to_strategy mapping")
    return ConfigurableDocumentProcessingManager(file_to_strategy)


def create_splitter():
    """
    Create a markdown splitter for chunking documents.
    """
    return CustomMarkdownSplitter(header_depth=3, chunk_size=512, chunk_overlap=128)


def create_embeddings_model():
    """
    Create and return the embeddings model.
    """
    model_kwargs = {"device": os.getenv("DEVICE_TYPE", "cpu")}
    return LangChainHuggingFaceEmbeddingModel(
        model_name=os.getenv("EMBEDDINGS_MODEL_NAME"),
        model_kwargs=model_kwargs,
        cache_folder="embeddings_cache",
    )


def create_vector_store(embeddings_model):
    """
    Create and return the remote vector store.
    """
    return RemoteVectorStore(
        url=os.getenv("VECTOR_STORE_URL"))


def create_llm():
    """
    Create and return the Azure OpenAI LLM.
    """
    return AzureOpenAILLM(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        model_version=os.getenv("AZURE_OPENAI_MODEL_VERSION"),
    )


def create_summarizer(llm):
    """
    Create and return the Summarizer.
    """
    return Summarizer(llm)


def create_tabular_summarizer(llm):
    """
    Create and return the Tabular Summarizer.
    """
    return TabularSummarizerLLM(llm=llm)


def create_tabular_llms(llm):
    """
    Create and return tabular-related LLM components.
    """
    return {
        "tabular_summarizer": TabularSummarizerLLM(llm=llm),
        "sql_generator": TabularSQLQueryGeneratorLLM(llm=llm),
        "question_queryable": QuestionQueryableLLM(llm=llm),
        "sql_corrector": SQLQueryCorrectorLLM(llm=llm),
        "recommendation_postprocessor": RecommendationSQLPostProcessorLLM(llm=llm),
    }


def create_tabular_vector_store(embeddings_model, tabular_llms):
    """
    Create and return the tabular Postgres vector store.
    """
    return TabularPGVectorStore(
        embedding_model=embeddings_model,
        tabular_sql_query_generator_llm=tabular_llms["sql_generator"],
        question_queryable_llm=tabular_llms["question_queryable"],
        sql_query_corrector_llm=tabular_llms["sql_corrector"],
        recommendation_sql_post_processor_llm=tabular_llms[
            "recommendation_postprocessor"
        ],
    )


def initialize_rag_services():
    """
    Initialize and return core shared services for rag.
    """
    embedding_model = create_embeddings_model()
    vector_store = create_vector_store(embedding_model)

    return {
        "vector_store": vector_store,
        "embedding_model": embedding_model,
    }


def initialize_document_services():
    """
    Initialize and return all services needed for document processing.
    """
    rag_services = get_rag_services()
    llm = get_llm()

    return {
        "vector_store": rag_services["vector_store"],
        "document_loader": create_document_loader(),
        "splitter": create_splitter(),
        "summarizer": create_summarizer(llm),
        "tabular_summarizer": create_tabular_summarizer(llm),
        "tabular_vector_store": create_tabular_vector_store(
            rag_services["embedding_model"], create_tabular_llms(llm)
        ),
    }


def initialize_tabular_vector_store():
    """
    Initialize and return the tabular vector store.
    """
    rag_services = get_rag_services()
    llm = get_llm()
    tabular_llms = create_tabular_llms(llm)
    return create_tabular_vector_store(rag_services["embedding_model"], tabular_llms)


def initialize_agent_services():
    """
    Initialize and return all services needed for agent processing.
    """
    rag_services = get_rag_services()
    llm = get_llm()
    tabular_vector_store = get_tabular_vector_store()

    return {
        "llm": llm,
        "tabular_vector_store": tabular_vector_store,
    }


_llm = None
_rag_services = None
_document_services = None
_tabular_vector_store = None
_agent_services = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = create_llm()
    return _llm


def get_tabular_vector_store():
    global _tabular_vector_store
    if _tabular_vector_store is None:
        _tabular_vector_store = initialize_tabular_vector_store()
    return _tabular_vector_store


def get_rag_services():
    global _rag_services
    if _rag_services is None:
        _rag_services = initialize_rag_services()
    return _rag_services


def get_document_services():
    global _document_services
    if _document_services is None:
        _document_services = initialize_document_services()
    return _document_services


def get_agent_services():
    global _agent_services
    if _agent_services is None:
        _agent_services = initialize_agent_services()
    return _agent_services
