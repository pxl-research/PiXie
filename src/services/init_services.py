from src.services.vectorstores.remote_rag_vectorstore import RemoteRagVectorStore
from src.services.vectorstores.remote_tabular_vectorstore import (
    RemoteTabularVectorStore,
)
from services.llms.azure_openai_llm import AzureOpenAILLM


import os


def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"{var_name} environment variable not set")
    return value


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


def initialize_document_services():
    """
    Initialize and return all services needed for document processing.
    """
    llm = create_llm()

    return {
        "llm": llm,
        "vector_store": create_rag_vector_store(),
        "tabular_vector_store": create_tabular_vector_store(),
    }


_services = None


def get_services():
    global _services
    if _services is None:
        _services = initialize_document_services()
    return _services
