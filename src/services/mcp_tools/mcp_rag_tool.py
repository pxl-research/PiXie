from services.embedding_models.lc_huggingface_embedding_model import (
    LangChainHuggingFaceEmbeddingModel,
)
from services.vectorstores.qdrant_vectorstore import QDrantVectorStore
from services.rerankers.bge_reranker import BGEReranker

from mcp.server.fastmcp import FastMCP
from typing import List, Tuple
import logging
import os

# Initialize FastMCP server with configuration
mcp = FastMCP(
    "RAG",  # Name of the MCP server
    instructions="You are a rag assistant that can retrieve information from document stored in the Qdrant vector store. The vector store contains information about the home working policy of Hogeschool PXL.",  # Instructions for the LLM on how to use this tool
)


def retrieve_and_rerank_chunks(
    collection_name: str,
    message: str,
    top_k: int = 15,
    final_k: int = 10,
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

    Returns:
        list[str]: A list of the final selected document chunks.
    """

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

    top_chunks = vector_store.retrieve_top_chunks(collection_name, message, top_k)

    final_chunks: list[str] = []
    if reranker is not None:
        final_chunks = reranker.rerank(message, top_chunks, final_k)
        logging.info(f"Chunks have been reranked for the message: {message}")
    else:
        final_chunks = top_chunks[:final_k]
        logging.info(
            f"No reranker available. Returning top {final_k} chunks for the message: {message}"
        )

    return final_chunks


def format_documents(final_docs):
    """
    Format retrieved documents into a string for processing.

    Parameters:
    - final_docs: list
        A list of document objects, where each document contains metadata and page content.

    Returns:
    - str: A formatted string of document references with file names and page numbers, each separated by new lines.
    """
    return "\n\n".join(
        [
            f"Bron: {doc.metadata.get('file_name', 'Onbekend bestand')} (pagina {doc.metadata.get('page_numbers', 'n.v.t.')})\n{doc.page_content}"
            for doc in final_docs
        ]
    )


@mcp.tool()
async def rag_search(question: str) -> List[str]:
    """
    Retrieve and format top-ranked chunks from the specified collection based on the question.

    Args:
        question (str): The question to retrieve relevant chunks for.
        collection_name (str): The name of the collection to search within.

    Returns:
        List[str]: A list of formatted document chunks relevant to the question.

    Raises:
        Exception: If there is an error while retrieving or formatting chunks, an exception is raised with details.
    """
    collection_name = "pixie"

    logging.info(
        f"Retrieving chunks for question: '{question}' from collection '{collection_name}'"
    )

    try:
        # Attempt to retrieve and rerank chunks
        final_docs = retrieve_and_rerank_chunks(collection_name, question)
        logging.info(
            f"Retrieved {len(final_docs)} documents for question: '{question}'"
        )

        # Format documents
        # docs = format_documents(final_docs)
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
