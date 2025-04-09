from mcp.server.fastmcp import FastMCP
from typing import List, Tuple
import logging
import os
import json
import pandas as pd
from langchain.schema import Document

from services.vectorstores.tabular_pg_vectorstore import TabularPGVectorStore
from services.llms.question_queryable_llm import QuestionQueryableLLM
from services.llms.recommendation_sql_post_processor_llm import (
    RecommendationSQLPostProcessorLLM,
)
from services.llms.sql_query_corrector_llm import SQLQueryCorrectorLLM
from services.llms.tabular_sql_query_generator_llm import TabularSQLQueryGeneratorLLM
from services.llms.tabular_summarizer_llm import TabularSummarizerLLM

from services.embedding_models.lc_huggingface_embedding_model import (
    LangChainHuggingFaceEmbeddingModel,
)

from services.llms.azure_openai_llm import AzureOpenAILLM


# Initialize FastMCP server with configuration
mcp = FastMCP(
    "Tabular-RAG",
    instructions="You are a tabular RAG assistant that can retrieve information from tabular data. You have information about garbage bins in Sint-Truiden",
)


def retrieve_and_rerank_chunks(
    collection_name: str, message: str, top_k: int = 15, final_k: int = 10
) -> list[str]:
    """
    Retrieve and optionally rerank document chunks based on the input message.

    This function retrieves the top `top_k` chunks relevant to the
    input `message` from the vector store.
    If a reranker is available, it reranks these chunks and
    returns the top `final_k` chunks.
    Otherwise, it simply returns the first `final_k` chunks from retrieved list.

    Parameters:
        collection_name (str): Name of the collection to retrieve rows from.
        message (str): Message used to retrieve relevant rows.
        top_k (int, optional): Number of top rows to retrieve initially. Default: 15.
        final_k (int, optional): Number of chunks to return after reranking. Default: 5.
        document_file_type (DocumentFileType, optional): Document type. Default: Document.

    Returns:
        list[str]: A list of the final selected document chunks.
    """

    model_kwargs = {"device": os.getenv("DEVICE_TYPE", "cpu")}

    embeddings_model = LangChainHuggingFaceEmbeddingModel(
        model_name=os.getenv("EMBEDDINGS_MODEL_NAME"),
        model_kwargs=model_kwargs,
        cache_folder="embeddings_cache",
    )

    llm = AzureOpenAILLM(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        api_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        model_version=os.getenv("AZURE_OPENAI_MODEL_VERSION"),
    )

    tabular_summarizer_llm = TabularSummarizerLLM(llm=llm)
    tabular_sql_query_generator_llm = TabularSQLQueryGeneratorLLM(llm=llm)
    question_queryable_llm = QuestionQueryableLLM(llm=llm)
    sql_query_corrector_llm = SQLQueryCorrectorLLM(llm=llm)
    recommendation_sql_post_processor_llm = RecommendationSQLPostProcessorLLM(llm=llm)

    tabular_vector_store = TabularPGVectorStore(
        embedding_model=embeddings_model,
        tabular_sql_query_generator_llm=tabular_sql_query_generator_llm,
        question_queryable_llm=question_queryable_llm,
        sql_query_corrector_llm=sql_query_corrector_llm,
        recommendation_sql_post_processor_llm=recommendation_sql_post_processor_llm,
    )

    top_chunks: list[Document] = []
    df_top_rows: pd.DataFrame = tabular_vector_store.retrieve_top_rows(
        collection_name=collection_name,
        question=message,
        top_k=top_k,  # Ensure `top_k` is defined in the scope
        k_rrf=60,
        max_file_count=3,
        try_iteration_max_count=3,
        is_recommendation_system=False,
    )
    top_dicts: list[dict] = df_top_rows.to_dict("records")

    top_chunks = [json.dumps(d) for d in top_dicts]
    # Omit reranker for TabularDocuments!
    final_chunks = top_chunks[:final_k]
    return final_chunks


@mcp.tool()
async def tabular_rag_search(question: str) -> List[str]:
    """
    Retrieve and format top-ranked rows from a tabular document in the specified collection based on the question using a tabular vector store.
    This is the default call for a tabular RAG search and should be done first.
    This is used for exact textual matching and numerical or datetime comparisons.

    Args:
        question (str): The question to retrieve relevant rows for.

    Returns:
        List[str]: A list of formatted rows relevant to the question.

    Raises:
        Exception: If there is an error while retrieving or formatting rows, an exception is raised with details.
    """
    collection_name = "pixie"

    logging.info(
        f"Retrieving chunks for question: '{question}' from collection '{collection_name}'"
    )
    try:
        # Attempt to retrieve and rerank chunks
        final_docs = retrieve_and_rerank_chunks(
            collection_name=collection_name,
            message=question,
            top_k=10,
            final_k=20,
        )
        logging.info(f"Retrieved {len(final_docs)} rows for question: '{question}'")
        # Format documents
        # if len(final_docs) > 0:
        #     docs = "\n".join(final_docs)
        # else:
        #     docs = "No answer found."

        logging.info(f"Formatted docs: {final_docs}")
        logging.info("Document formatting completed successfully.")
        return final_docs

    except Exception as e:
        # Log any exceptions that occur during retrieval or formatting
        logging.error(
            f"Error in retrieving or formatting chunks for question '{question}': {e}"
        )
        return [f"Error during retrieval: {e}"]


if __name__ == "__main__":
    # Start the MCP server with stdio transport
    # stdio transport allows the server to communicate with clients
    # through standard input/output streams, making it suitable for
    # local development and testing
    mcp.run(transport="stdio")
