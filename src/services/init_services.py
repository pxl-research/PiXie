from services.document_loaders.document_loader_manager import (
    ConfigurableDocumentProcessingManager,
)
from services.splitters.custom_markdown_splitter import CustomMarkdownSplitter

from src.services.vectorstores.remote_rag_vectorstore import RemoteRagVectorStore
from src.services.vectorstores.remote_tabular_vectorstore import (
    RemoteTabularVectorStore,
)
from services.llms.azure_openai_llm import AzureOpenAILLM
from services.summarizer import Summarizer
from services.llms.tabular_summarizer_llm import TabularSummarizerLLM


import os
import logging

def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"{var_name} environment variable not set")
    return value


def create_document_loader():
    """
    Create a document loader manager using file_to_strategy.
    """
    logging.info("Creating document loader manager ...")
    file_to_strategy: dict[str, str] = {
        "docx": get_required_env("DOCX_STRATEGY"),
        "doc": get_required_env("DOCX_STRATEGY"),
        # "odt": get_required_env("DOCX_STRATEGY"),
        # "rtf": get_required_env("DOCX_STRATEGY"),
        "pdf": get_required_env("PDF_STRATEGY"),
        "pptx": get_required_env("PPTX_STRATEGY"),
        # "odp": get_required_env("PPTX_STRATEGY"),
        "csv": get_required_env("CSV_STRATEGY"),
        "xlsx": get_required_env("XLSX_STRATEGY"),
        "xls": get_required_env("XLSX_STRATEGY"),
        # "ods": get_required_env("XLSX_STRATEGY"),
        # "md": get_required_env("MD_STRATEGY"),
    }
    logging.info("Loaded the file_to_strategy mapping")
    return ConfigurableDocumentProcessingManager(file_to_strategy)


def create_splitter():
    """
    Create a markdown splitter for chunking documents.
    """
    return CustomMarkdownSplitter(header_depth=3, chunk_size=512, chunk_overlap=128)


def create_rag_vector_store():
    """
    Create and return the remote rag vector store.
    """
    rag_url = get_required_env("RAG_URL")
    return RemoteRagVectorStore(url=rag_url)


def create_tabular_vector_store():
    """
    Create and return the remote tabular vector store.
    """
    tabular_url = get_required_env("TABULAR_URL")
    return RemoteTabularVectorStore(url=tabular_url)


def create_llm():
    """
    Create and return the Azure OpenAI LLM.
    """
    api_version = get_required_env("AZURE_OPENAI_API_VERSION")
    api_endpoint = get_required_env("AZURE_OPENAI_ENDPOINT")
    api_key = get_required_env("AZURE_OPENAI_API_KEY")
    model_version = get_required_env("AZURE_OPENAI_MODEL_VERSION")
    return AzureOpenAILLM(
        api_version=api_version,
        api_endpoint=api_endpoint,
        api_key=api_key,
        model_version=model_version,
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


def initialize_document_services():
    """
    Initialize and return all services needed for document processing.
    """
    llm = create_llm()

    return {
        "llm": llm,
        "vector_store": create_rag_vector_store(),
        "document_loader": create_document_loader(),
        "splitter": create_splitter(),
        "summarizer": create_summarizer(llm),
        "tabular_summarizer": create_tabular_summarizer(llm),
        "tabular_vector_store": create_tabular_vector_store(),
    }


_services = None


def get_services():
    global _services
    if _services is None:
        _services = initialize_document_services()
    return _services
