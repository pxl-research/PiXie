from typing import List, Tuple
import logging
from datetime import datetime

from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults

from services import document_manager
from services.document_loaders.document_loader_manager import DocumentFileType


@tool("get_date")
def get_date(format: str = "%Y-%m-%d") -> str:
    """
    Returns the current date in the specified format.

    Args:
        format (str): The format in which to return the date. Default is "%Y-%m-%d".

    Returns:
        str: The current date formatted according to the specified format.
    """
    current_date = datetime.now().strftime(format)
    return current_date


@tool("weather_api")
def weather_api(question: str) -> str:
    """
    Get the weather today for Hasselt.

    Args:
        question (str): The question asked.

    Returns:
        str: The weather today in Hasselt.
    """
    logging.info("Get the weather in Hasselt ...")
    return "In Hasselt gaat de zon schijnen en wordt het 20 graden."


@tool("web_search")
def web_search(question: str) -> str:
    """
    Perform a web search based on the provided question using the Tavily search API.

    Args:
        question (str): The question or search query to look up.

    Returns:
        str: The summarized search results for the question, including relevant content from top sources.

    Raises:
        Exception: If there is an error while invoking the search, an exception is raised with a relevant message.
    """
    logging.info(f"Performing web search for question: '{question}'")

    # Initialize the search tool with specific parameters
    search_tool = TavilySearchResults(
        max_results=3,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
        include_domains=[
            "https://www.pxl.be/*",
            "https://www.pxlexperts.be/*",
            "https://www.pxl-research.be/*",
        ],
    )

    try:
        # Execute the search and return results
        results = search_tool.invoke(question)
        logging.info("Web search completed successfully.")

        # Format each result with title, URL, and summary if available
        formatted_results = []
        for result in results:
            title = result.get("title", "No Title")
            url = result.get("url", "No URL")
            summary = result.get("content", "No summary available")
            formatted_results.append(f"Bron: [{url}]({url}\n{summary}")

        # Join all formatted results into a single string
        return "\n".join(formatted_results)
    except Exception as e:
        # Log the error with an appropriate message
        logging.error(
            f"Error occurred during web search for question '{question}': {e}"
        )
        return f"Error during search: {e}"


@tool("rag_search")
def rag_search(question: str, collection_name: str) -> List[str]:
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
    logging.info(
        f"Retrieving chunks for question: '{question}' from collection '{collection_name}'"
    )

    try:
        # Attempt to retrieve and rerank chunks
        final_docs = document_manager.retrieve_and_rerank_chunks(
            collection_name, question, document_file_type=DocumentFileType.Document
        )
        logging.info(
            f"Retrieved {len(final_docs)} documents for question: '{question}'"
        )

        # Format documents
        docs = format_documents(final_docs)
        logging.info("Document formatting completed successfully.")
        return docs

    except Exception as e:
        # Log any exceptions that occur during retrieval or formatting
        logging.error(
            f"Error in retrieving or formatting chunks for question '{question}': {e}"
        )
        return [f"Error during retrieval: {e}"]


@tool("tabular_rag_search")
def tabular_rag_search(question: str, collection_name: str) -> List[str]:
    """
    Retrieve and format top-ranked rows from a tabular document in the specified collection based on the question using a tabular vector store.

    Args:
        question (str): The question to retrieve relevant rows for.
        collection_name (str): The name of the collection to search within.

    Returns:
        List[str]: A list of formatted rows relevant to the question.

    Raises:
        Exception: If there is an error while retrieving or formatting rows, an exception is raised with details.
    """
    logging.info(
        f"Retrieving chunks for question: '{question}' from collection '{collection_name}'"
    )
    try:
        # Attempt to retrieve and rerank chunks
        final_docs = document_manager.retrieve_and_rerank_chunks(
            collection_name, question, document_file_type=DocumentFileType.TabularDocument
        )
        logging.info(
            f"Retrieved {len(final_docs)} rows for question: '{question}'"
        )
        # Format documents
        docs = format_documents(final_docs)
        logging.info("Document formatting completed successfully.")
        return docs

    except Exception as e:
        # Log any exceptions that occur during retrieval or formatting
        logging.error(
            f"Error in retrieving or formatting chunks for question '{question}': {e}"
        )
        return [f"Error during retrieval: {e}"]


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


@tool("final_answer")
def final_answer(answer: str, sources: str) -> Tuple[str, str]:
    """
    Generate a final answer and return it along with sources as separate outputs.

    Args:
        answer (str): The generated answer text.
        sources (str): Source information related to the answer.

    Returns:
        Tuple[str, str]: The final answer and sources as separate values.
    """
    logging.info("Generating final answer...")
    logging.debug(f"Answer: {answer}")
    logging.debug(f"Sources: {sources}")

    return answer, sources
